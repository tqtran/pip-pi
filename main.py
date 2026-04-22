#!/usr/bin/env python3
"""
pip-pi dashboard prototype.

Reference-inspired neon layout using rectangles, lines, and text only.
No image assets required.
"""

import math
import os
import shutil
import subprocess
import sys
import time
from array import array

import pygame

WIDTH, HEIGHT = 720, 480
FPS = 30
DATA_REFRESH_SECONDS = 5.0
RIPPLE_LIFE = 0.45

BG = (4, 6, 16)
PANEL_BG = (8, 10, 24)
TEXT = (224, 230, 238)
MUTED = (116, 136, 158)
PINK = (255, 14, 142)
CYAN = (0, 197, 255)
VIOLET = (122, 56, 255)
RED = (255, 36, 36)
WHITE = (255, 255, 255)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def c_to_f(celsius):
    return (celsius * 9.0 / 5.0) + 32.0


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def run_command_lines(cmd):
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=2)
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        return []


def parse_cpu_snapshot():
    line = read_text("/proc/stat")
    if not line:
        return None
    first = line.splitlines()[0].split()
    if len(first) < 8 or first[0] != "cpu":
        return None
    vals = [int(x) for x in first[1:8]]
    idle = vals[3] + vals[4]
    total = sum(vals)
    return total, idle


def read_cpu_percent(cache):
    snap = parse_cpu_snapshot()
    if snap is None:
        return cache.get("cpu", 0)

    prev = cache.get("cpu_prev")
    if prev is None:
        # First sample: take a short second snapshot to compute a real percentage.
        time.sleep(0.08)
        snap2 = parse_cpu_snapshot()
        if snap2 is None:
            cache["cpu_prev"] = snap
            return cache.get("cpu", 0)
        total_delta = snap2[0] - snap[0]
        idle_delta = snap2[1] - snap[1]
        cache["cpu_prev"] = snap2
        if total_delta <= 0:
            return cache.get("cpu", 0)
        cpu = clamp(int(100.0 * (1.0 - (idle_delta / float(total_delta)))), 0, 100)
        cache["cpu"] = cpu
        return cpu

    cache["cpu_prev"] = snap

    total_delta = snap[0] - prev[0]
    idle_delta = snap[1] - prev[1]
    if total_delta <= 0:
        return cache.get("cpu", 0)
    cpu = clamp(int(100.0 * (1.0 - (idle_delta / float(total_delta)))), 0, 100)
    cache["cpu"] = cpu
    return cpu


def read_mem_percent():
    meminfo = read_text("/proc/meminfo")
    if not meminfo:
        return None

    vals = {}
    for line in meminfo.splitlines():
        parts = line.split(":", 1)
        if len(parts) != 2:
            continue
        key = parts[0]
        try:
            vals[key] = int(parts[1].strip().split()[0])
        except Exception:
            continue

    total = vals.get("MemTotal")
    avail = vals.get("MemAvailable")
    if not total or avail is None:
        return None
    used = 100.0 * (1.0 - (avail / float(total)))
    return clamp(int(used), 0, 100)


def read_storage_percent():
    try:
        usage = shutil.disk_usage("/")
        if usage.total <= 0:
            return None
        return clamp(int(100.0 * (usage.used / float(usage.total))), 0, 100)
    except Exception:
        return None


def read_temp_c():
    # Standard Pi thermal sensor path.
    raw = read_text("/sys/class/thermal/thermal_zone0/temp")
    if raw:
        try:
            return float(raw) / 1000.0
        except Exception:
            pass
    return None


def read_wifi_count():
    # Best effort: nearby AP scan count via nmcli when available.
    lines = run_command_lines(["nmcli", "-t", "-f", "SSID", "dev", "wifi", "list"])
    if not lines:
        return None
    unique = {ln for ln in lines if ln}
    return len(unique)


def read_ble_count():
    # Best effort: known bluetooth devices count from bluetoothctl.
    lines = run_command_lines(["bluetoothctl", "devices"])
    if not lines:
        return None
    return len(lines)


def read_uptime_str():
    txt = read_text("/proc/uptime")
    if txt:
        try:
            elapsed = int(float(txt.split()[0]))
            hh = elapsed // 3600
            mm = (elapsed % 3600) // 60
            ss = elapsed % 60
            return f"{hh:01d}:{mm:02d}:{ss:02d}"
        except Exception:
            pass

    # Fallback to process uptime if system uptime is unavailable.
    return None


def init_pygame_or_die():
    """Initialize pygame and verify font support with a concrete render test."""
    print(f"[startup] python: {sys.executable}")
    print(f"[startup] pygame: {getattr(pygame, '__file__', 'unknown')}")

    pygame.init()
    try:
        if not hasattr(pygame, "font"):
            raise RuntimeError("pygame.font module is missing")

        pygame.font.init()
        test_font = pygame.font.SysFont("dejavusansmono", 16, bold=True)
        test_font.render("font-ok", True, TEXT)
        print("[startup] pygame.font: ok")
    except Exception as exc:
        print(f"[startup] pygame.font failed: {exc}")
        print("[startup] likely causes: broken pygame install, missing SDL_ttf, or local module shadowing")
        pygame.quit()
        raise SystemExit(1)


def init_click_sound():
    """Create a short synthesized click tone. Returns None if audio is unavailable."""
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=256)

        sample_rate = 22050
        duration_s = 0.05
        freq_hz = 1400.0
        total = int(sample_rate * duration_s)
        pcm = array("h")
        for i in range(total):
            t = i / float(sample_rate)
            envelope = 1.0 - (i / float(total))
            sample = int(14000 * envelope * math.sin(2.0 * math.pi * freq_hz * t))
            pcm.append(sample)

        return pygame.mixer.Sound(buffer=pcm.tobytes())
    except Exception:
        return None


def neon_box(screen, rect, border, fill=PANEL_BG, radius=8):
    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    glow = rect.inflate(6, 6)
    pygame.draw.rect(screen, (border[0] // 4, border[1] // 4, border[2] // 4), glow, 1, border_radius=radius + 2)
    pygame.draw.rect(screen, border, rect, 2, border_radius=radius)


def text_surf(font, s, color=TEXT):
    return font.render(s, True, color)


def draw_metric_bar(screen, x, y, value, color):
    blocks = 8
    on = int(round(clamp(value, 0, 100) / 100 * blocks))
    w, h, gap = 10, 12, 2
    for i in range(blocks):
        c = color if i < on else (28, 34, 62)
        pygame.draw.rect(screen, c, (x + i * (w + gap), y, w, h), border_radius=2)


def draw_wire_grid(screen, rect, color):
    for i in range(1, 8):
        yy = rect.y + int(i * rect.h / 8)
        pygame.draw.line(screen, (color[0] // 5, color[1] // 5, color[2] // 5), (rect.x + 6, yy), (rect.right - 6, yy), 1)
    for i in range(1, 10):
        xx = rect.x + int(i * rect.w / 10)
        pygame.draw.line(screen, (color[0] // 6, color[1] // 6, color[2] // 6), (xx, rect.y + 6), (xx, rect.bottom - 6), 1)


def draw_wifi_symbol(screen, cx, cy, color):
    # WiFi arcs above a dot (upright orientation).
    center_y = cy - 6
    for r, th in ((36, 5), (25, 4), (14, 4)):
        rect = pygame.Rect(cx - r, center_y - r, 2 * r, 2 * r)
        pygame.draw.arc(screen, color, rect, math.radians(30), math.radians(150), th)
    pygame.draw.circle(screen, color, (cx, center_y + 18), 6)


def draw_bluetooth_symbol(screen, cx, cy, color):
    # Canonical Bluetooth rune with both right and left whiskers.
    top = (cx, cy - 34)
    mid = (cx, cy)
    bot = (cx, cy + 34)
    up_r = (cx + 20, cy - 16)
    dn_r = (cx + 20, cy + 16)
    up_l = (cx - 18, cy - 16)
    dn_l = (cx - 18, cy + 16)

    pygame.draw.line(screen, color, top, bot, 4)
    pygame.draw.line(screen, color, top, up_r, 4)
    pygame.draw.line(screen, color, top, up_l, 4)
    pygame.draw.line(screen, color, mid, up_r, 4)
    pygame.draw.line(screen, color, mid, up_l, 4)
    pygame.draw.line(screen, color, mid, dn_r, 4)
    pygame.draw.line(screen, color, mid, dn_l, 4)
    pygame.draw.line(screen, color, bot, dn_r, 4)
    pygame.draw.line(screen, color, bot, dn_l, 4)


def draw_capture_symbol(screen, cx, cy, color):
    pts = [(cx - 18, cy), (cx - 10, cy), (cx - 3, cy - 10), (cx + 5, cy + 10), (cx + 13, cy), (cx + 21, cy)]
    pygame.draw.lines(screen, color, False, pts, 3)
    pygame.draw.circle(screen, color, (cx - 18, cy), 2)
    pygame.draw.circle(screen, color, (cx + 21, cy), 2)


def draw_system_symbol(screen, cx, cy, color):
    pygame.draw.rect(screen, color, (cx - 11, cy - 11, 22, 22), 2, border_radius=3)
    pygame.draw.rect(screen, color, (cx - 5, cy - 5, 10, 10), 2, border_radius=2)
    for dx, dy in ((0, -16), (0, 16), (-16, 0), (16, 0), (-12, -12), (12, -12), (-12, 12), (12, 12)):
        pygame.draw.line(screen, color, (cx + dx, cy + dy), (cx + dx // 2, cy + dy // 2), 2)


def draw_logs_symbol(screen, cx, cy, color):
    pygame.draw.rect(screen, color, (cx - 12, cy - 15, 24, 30), 2, border_radius=3)
    pygame.draw.line(screen, color, (cx - 7, cy - 7), (cx + 7, cy - 7), 2)
    pygame.draw.line(screen, color, (cx - 7, cy), (cx + 7, cy), 2)
    pygame.draw.line(screen, color, (cx - 7, cy + 7), (cx + 3, cy + 7), 2)


def draw_menu_symbol(screen, idx, cx, cy, color):
    if idx == 0:
        draw_wifi_symbol(screen, cx, cy - 2, color)
    elif idx == 1:
        draw_bluetooth_symbol(screen, cx, cy, color)
    elif idx == 2:
        draw_capture_symbol(screen, cx, cy, color)
    elif idx == 3:
        draw_system_symbol(screen, cx, cy, color)
    else:
        draw_logs_symbol(screen, cx, cy, color)


def draw_bottom_pulse_strip(screen, t):
    strip = pygame.Rect(14, 12, WIDTH - 28, 14)
    segs = 40
    gap = 2
    seg_w = (strip.w - (segs - 1) * gap) // segs
    cycle = (segs - 1) * 2
    phase = (t * 9.0) % cycle
    head = phase if phase <= (segs - 1) else (cycle - phase)

    for i in range(segs):
        dist = abs(i - head)
        glow = max(0.06, 1.0 - dist / 6.0)
        boost = 0.18 + 1.25 * glow
        c = (
            clamp(int(RED[0] * boost), 0, 255),
            clamp(int(RED[1] * boost), 0, 255),
            clamp(int(RED[2] * boost), 0, 255),
        )
        x = strip.x + i * (seg_w + gap)
        pygame.draw.rect(screen, c, (x, strip.y, seg_w, strip.h), border_radius=2)


def draw_ripples(screen, ripples, now):
    if not ripples:
        return

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for rp in ripples:
        age = now - rp["born"]
        if age >= RIPPLE_LIFE:
            continue

        p = age / RIPPLE_LIFE
        alpha = int(180 * (1.0 - p))
        base_r = 10 + int(58 * p)
        for k in range(3):
            r = base_r + k * 14
            a = max(0, alpha - k * 35)
            if a > 0:
                pygame.draw.circle(overlay, (WHITE[0], WHITE[1], WHITE[2], a), (rp["x"], rp["y"]), r, 2)

    screen.blit(overlay, (0, 0))


def draw_status_panel(screen, rect, fonts, data):
    neon_box(screen, rect, VIOLET)
    title = text_surf(fonts["panel_title"], "SYSTEM STATS", TEXT)
    screen.blit(title, (rect.x + 12, rect.y + 10))

    temp_f = c_to_f(data["temp"])
    labels = [
        ("STORE", data["store"], VIOLET),
        ("TEMP", temp_f, VIOLET),
    ]
    col_w = (rect.w - 24) // 3
    for i, (name, val, color) in enumerate(labels):
        x = rect.x + 12 + i * col_w
        screen.blit(text_surf(fonts["sm"], name, MUTED), (x, rect.y + 48))
        screen.blit(text_surf(fonts["stat_val"], f"{int(val)}%" if name != "TEMP" else f"{int(val)}F", color), (x, rect.y + 86))
        draw_metric_bar(screen, x, rect.y + 114, val if name != "TEMP" else ((val - 86) * 1.2), color)
        if i < 2:
            pygame.draw.line(screen, (36, 43, 73), (x + col_w - 8, rect.y + 38), (x + col_w - 8, rect.bottom - 16), 1)

    up_x = rect.x + 12 + 2 * col_w
    screen.blit(text_surf(fonts["sm"], "UPTIME", MUTED), (up_x, rect.y + 48))
    screen.blit(text_surf(fonts["stat_val"], data["uptime"], VIOLET), (up_x, rect.y + 92))


def draw_cpu_mem_panel(screen, rect, fonts, data):
    neon_box(screen, rect, CYAN)
    screen.blit(text_surf(fonts["panel_title"], "SYSTEM LOAD", TEXT), (rect.x + 12, rect.y + 10))

    col_w = (rect.w - 24) // 2
    items = [("CPU", data["cpu"], CYAN), ("MEM", data["mem"], CYAN)]
    for i, (name, val, color) in enumerate(items):
        x = rect.x + 12 + i * col_w
        screen.blit(text_surf(fonts["sm"], name, MUTED), (x, rect.y + 48))
        screen.blit(text_surf(fonts["stat_val"], f"{int(val)}%", color), (x + 70, rect.y + 46))
        draw_metric_bar(screen, x, rect.y + 90, val, color)
        if i == 0:
            pygame.draw.line(screen, (36, 43, 73), (x + col_w - 8, rect.y + 38), (x + col_w - 8, rect.bottom - 16), 1)


def draw_main(screen, fonts, data, selected, now):
    screen.fill(BG)

    outer = pygame.Rect(6, 6, WIDTH - 12, HEIGHT - 12)
    neon_box(screen, outer, (24, 94, 120), fill=(2, 4, 12), radius=10)

    # Top bar
    top = pygame.Rect(14, 20, WIDTH - 28, 34)
    pygame.draw.line(screen, (20, 35, 60), (top.x, top.bottom), (top.right, top.bottom), 1)
    screen.blit(text_surf(fonts["top"], "KAGE // LVL 27", PINK), (top.x + 10, top.y + 8))
    live = text_surf(fonts["top"], "LIVE INTEL", PINK)
    screen.blit(live, (WIDTH // 2 - live.get_width() // 2, top.y + 8))
    clock_text = text_surf(fonts["top"], data["clock"], PINK)
    screen.blit(clock_text, (top.right - 122, top.y + 8))

    # Left menu
    left = pygame.Rect(14, 54, 170, HEIGHT - 68)
    menu_items = ["WIFI", "BLUETOOTH", "CAPTURE", "SYSTEM", "LOGS"]
    menu_colors = [PINK, CYAN, VIOLET, VIOLET, CYAN]
    tile_h = 78
    for i, name in enumerate(menu_items):
        r = pygame.Rect(left.x, left.y + i * (tile_h + 8), left.w, tile_h)
        col = menu_colors[i]
        fill = (20, 8, 28) if i == selected else (5, 8, 20)
        neon_box(screen, r, col, fill=fill)
        screen.blit(text_surf(fonts["menu"], name, TEXT), (r.x + 18, r.y + 28))

    # Right content
    rx = left.right + 10
    rw = WIDTH - rx - 14

    wifi = pygame.Rect(rx, 54, rw, 130)
    neon_box(screen, wifi, PINK)
    draw_wire_grid(screen, wifi.inflate(-8, -10), PINK)
    screen.blit(text_surf(fonts["panel_title"], "WIFI FOUND", TEXT), (wifi.x + 18, wifi.y + 14))
    screen.blit(text_surf(fonts["wifi_num"], str(data["wifi"]), PINK), (wifi.x + 18, wifi.y + 54))
    split_x = wifi.x + (wifi.w // 2)
    pygame.draw.line(screen, (90, 20, 60), (split_x, wifi.y + 20), (split_x, wifi.bottom - 20), 2)
    screen.blit(text_surf(fonts["panel_title"], "BLE FOUND", TEXT), (split_x + 18, wifi.y + 14))
    screen.blit(text_surf(fonts["wifi_num"], str(data["ble"]), CYAN), (split_x + 18, wifi.y + 54))

    cpu_mem = pygame.Rect(rx, 194, rw, 108)
    draw_cpu_mem_panel(screen, cpu_mem, fonts, data)

    stats = pygame.Rect(rx, 312, rw, HEIGHT - 326)
    draw_status_panel(screen, stats, fonts, data)

    draw_bottom_pulse_strip(screen, now)


def make_fonts():
    # Fall back to defaults automatically; this still requires pygame font support.
    return {
        "sm": pygame.font.SysFont("dejavusansmono", 20, bold=True),
        "top": pygame.font.SysFont("dejavusansmono", 17, bold=True),
        "menu": pygame.font.SysFont("dejavusansmono", 27, bold=True),
        "panel_title": pygame.font.SysFont("dejavusansmono", 26, bold=True),
        "lg": pygame.font.SysFont("dejavusansmono", 54, bold=True),
        "stat_val": pygame.font.SysFont("dejavusansmono", 27, bold=True),
        "wifi_num": pygame.font.SysFont("dejavusansmono", 52, bold=True),
    }


def update_data(data, cache, start_time):
    cpu = read_cpu_percent(cache)
    mem = read_mem_percent()
    store = read_storage_percent()
    temp_c = read_temp_c()
    wifi = read_wifi_count()
    ble = read_ble_count()
    uptime = read_uptime_str()

    if cpu is not None:
        data["cpu"] = cpu
    if mem is not None:
        data["mem"] = mem
    if store is not None:
        data["store"] = store
    if temp_c is not None:
        data["temp"] = clamp(temp_c, -40.0, 140.0)
    if wifi is not None:
        data["wifi"] = clamp(wifi, 0, 999)
    if ble is not None:
        data["ble"] = clamp(ble, 0, 999)

    data["clock"] = time.strftime("%H:%M")
    if uptime is not None:
        data["uptime"] = uptime
    else:
        elapsed = int(time.time() - start_time)
        hh = elapsed // 3600
        mm = (elapsed % 3600) // 60
        ss = elapsed % 60
        data["uptime"] = f"{hh:01d}:{mm:02d}:{ss:02d}"


def main():
    init_pygame_or_die()
    pygame.display.set_caption("pip-pi live intel")
    pygame.mouse.set_visible(False)

    flags = pygame.FULLSCREEN if "--fullscreen" in set(sys.argv[1:]) else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    clock = pygame.time.Clock()

    fonts = make_fonts()
    click_sound = init_click_sound()
    selected = 0
    start = time.time()
    last_data = -DATA_REFRESH_SECONDS
    data = {
        "wifi": 12,
        "ble": 7,
        "cpu": 45,
        "mem": 61,
        "store": 45,
        "temp": 62,
        "clock": "00:00",
        "uptime": "0:00:00",
    }
    cache = {}
    ripples = []

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % 5
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % 5
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                ripples.append({"x": mx, "y": my, "born": time.time()})
                if click_sound is not None:
                    click_sound.play()
                if 14 <= mx <= 184:
                    tile_h = 78
                    start_y = 54
                    for i in range(5):
                        y = start_y + i * (tile_h + 8)
                        if y <= my <= y + tile_h:
                            selected = i
                            break

        now = time.time()
        if now - last_data >= DATA_REFRESH_SECONDS:
            update_data(data, cache, start)
            last_data = now

        draw_main(screen, fonts, data, selected, now)
        draw_ripples(screen, ripples, now)

        # Keep only active ripple effects.
        ripples = [rp for rp in ripples if (now - rp["born"]) < RIPPLE_LIFE]
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
