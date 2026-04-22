#!/usr/bin/env python3
"""
pip-pi dashboard prototype.

Reference-inspired neon layout using rectangles, lines, and text only.
No image assets required.
"""

import math
import json
import os
import shutil
import subprocess
import sys
import time
from array import array

import pygame

# Base design resolution — all pixel values are authored at this size.
BASE_W, BASE_H = 720, 480
WIDTH, HEIGHT = BASE_W, BASE_H  # overridden at runtime from the display
SCALE = 1.0                      # set in main() after pygame.init()


def S(n):
    """Scale a base-resolution pixel value proportionally to the current resolution."""
    return int(round(n * SCALE))


FPS = 30
RIPPLE_LIFE = 0.45
CONFIG_PATH = "pip-pi.config.json"

DEFAULT_CONFIG = {
    "scan_intervals": {
        "ble_seconds": 60.0,
        "wifi_seconds": 60.0,
    },
    "refresh_intervals": {
        "load_seconds": 5.0,
        "stats_seconds": 60.0,
    },
}

SCAN_ANIM_SECS = 3.0  # seconds to display scanning indicator after each scan


def clone_default_config():
    return {
        "scan_intervals": {
            "ble_seconds": DEFAULT_CONFIG["scan_intervals"]["ble_seconds"],
            "wifi_seconds": DEFAULT_CONFIG["scan_intervals"]["wifi_seconds"],
        },
        "refresh_intervals": {
            "load_seconds": DEFAULT_CONFIG["refresh_intervals"]["load_seconds"],
            "stats_seconds": DEFAULT_CONFIG["refresh_intervals"]["stats_seconds"],
        },
    }


def write_config_file(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, sort_keys=True)


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                return cfg
            print(f"[config] invalid root type in {CONFIG_PATH}; using defaults")
        except Exception as exc:
            print(f"[config] failed to read {CONFIG_PATH}: {exc}; using defaults")

    cfg = clone_default_config()
    try:
        write_config_file(cfg)
        print(f"[config] wrote default config: {CONFIG_PATH}")
    except Exception as exc:
        print(f"[config] failed to write default config {CONFIG_PATH}: {exc}")
    return cfg


CONFIG = load_config()

BG = (4, 6, 16)
PANEL_BG = (8, 10, 24)
TEXT = (224, 230, 238)
MUTED = (116, 136, 158)
PINK = (255, 14, 142)
CYAN = (0, 197, 255)
VIOLET = (122, 56, 255)
RED = (255, 36, 36)
WHITE = (255, 255, 255)
FLASHLIGHT = (255, 255, 255)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def c_to_f(celsius):
    return (celsius * 9.0 / 5.0) + 32.0


def scale_color(color, factor):
    return tuple(clamp(int(c * factor), 0, 255) for c in color)


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
    # Force a fresh scan so the result is live, not cached.
    lines = run_command_lines(["nmcli", "-t", "-f", "SSID", "dev", "wifi", "list", "--rescan", "yes"])
    if not lines:
        return 0
    unique = {ln for ln in lines if ln}
    return len(unique)


def read_ble_count():
    # Best effort: known bluetooth devices count from bluetoothctl.
    lines = run_command_lines(["bluetoothctl", "devices"])
    if not lines:
        return 0
    return len(lines)


def read_uptime_str():
    txt = read_text("/proc/uptime")
    if txt:
        try:
            elapsed = int(float(txt.split()[0]))
            hh = elapsed // 3600
            mm = (elapsed % 3600) // 60
            return f"{hh:01d}:{mm:02d}"
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


def neon_box(screen, rect, border, fill=PANEL_BG, radius=8, pulse=0.0):
    pulse_factor = 0.88 + 0.18 * (0.5 + 0.5 * math.sin(pulse))
    glow_color = scale_color(border, 0.22 + 0.18 * (0.5 + 0.5 * math.sin(pulse)))
    line_color = scale_color(border, pulse_factor)
    sr = max(1, S(radius))
    pygame.draw.rect(screen, fill, rect, border_radius=sr)
    glow = rect.inflate(S(6), S(6))
    pygame.draw.rect(screen, glow_color, glow, 1, border_radius=sr + S(2))
    pygame.draw.rect(screen, line_color, rect, 2, border_radius=sr)


def draw_active_button_shimmer(screen, rect, now):
    """Draw a moving highlight segment along a button border."""
    overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    w, h = rect.w - 1, rect.h - 1
    perim = max(1, 2 * (w + h))
    head = int((now * 220.0) % perim)
    seg_len = 34

    def point_at(d):
        d %= perim
        if d < w:
            return d, 0
        d -= w
        if d < h:
            return w, d
        d -= h
        if d < w:
            return w - d, h
        d -= w
        return 0, h - d

    # Draw discrete samples along the perimeter path to avoid diagonal cuts.
    for j in range(seg_len):
        d = (head - j) % perim
        x, y = point_at(d)
        alpha = clamp(190 - j * 6, 24, 190)
        overlay.set_at((x, y), (255, 255, 255, alpha))
        if x + 1 < rect.w:
            overlay.set_at((x + 1, y), (255, 255, 255, alpha // 2))
    screen.blit(overlay, rect.topleft)


def text_surf(font, s, color=TEXT):
    return font.render(s, True, color)


def draw_metric_bar(screen, x, y, value, color):
    blocks = 8
    on = int(round(clamp(value, 0, 100) / 100 * blocks))
    w, h, gap = max(1, S(10)), max(1, S(12)), max(1, S(2))
    for i in range(blocks):
        c = color if i < on else (28, 34, 62)
        pygame.draw.rect(screen, c, (x + i * (w + gap), y, w, h), border_radius=2)


def draw_scanline_shimmer(screen, rect, now):
    overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bright_y = int((now * 48) % max(1, rect.h))
    for y in range(0, rect.h, 4):
        alpha = 7
        if abs(y - bright_y) < 2:
            alpha = 18
        elif abs(y - bright_y) < 8:
            alpha = 10
        pygame.draw.line(overlay, (255, 255, 255, alpha), (0, y), (rect.w, y), 1)
    screen.blit(overlay, rect.topleft)


def draw_last_update(screen, fonts, data, top_rect, now):
    stamp = data.get("last_update", "--:--:--")
    label = text_surf(fonts["tiny"], f"UPDATED {stamp}", MUTED)
    dot_on = int(now * 2) % 2 == 0
    x = top_rect.right - S(250)
    y = top_rect.y + S(11)
    if dot_on:
        pygame.draw.circle(screen, CYAN, (x, y + S(5)), 3)
    screen.blit(label, (x + S(10), y - S(4)))


def draw_wire_grid(screen, rect, color):
    for i in range(1, 8):
        yy = rect.y + int(i * rect.h / 8)
        pygame.draw.line(screen, (color[0] // 5, color[1] // 5, color[2] // 5), (rect.x + 6, yy), (rect.right - 6, yy), 1)
    for i in range(1, 10):
        xx = rect.x + int(i * rect.w / 10)
        pygame.draw.line(screen, (color[0] // 6, color[1] // 6, color[2] // 6), (xx, rect.y + 6), (xx, rect.bottom - 6), 1)


def draw_wifi_symbol(screen, cx, cy, color):
    # WiFi arcs above a dot (upright orientation).
    center_y = cy - S(6)
    for r, th in ((S(36), 5), (S(25), 4), (S(14), 4)):
        rect = pygame.Rect(cx - r, center_y - r, 2 * r, 2 * r)
        pygame.draw.arc(screen, color, rect, math.radians(30), math.radians(150), th)
    pygame.draw.circle(screen, color, (cx, center_y + S(18)), max(1, S(6)))


def draw_bluetooth_symbol(screen, cx, cy, color):
    # Canonical Bluetooth rune with both right and left whiskers.
    top = (cx, cy - S(34))
    mid = (cx, cy)
    bot = (cx, cy + S(34))
    up_r = (cx + S(20), cy - S(16))
    dn_r = (cx + S(20), cy + S(16))
    up_l = (cx - S(18), cy - S(16))
    dn_l = (cx - S(18), cy + S(16))

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
    pts = [(cx - S(18), cy), (cx - S(10), cy), (cx - S(3), cy - S(10)), (cx + S(5), cy + S(10)), (cx + S(13), cy), (cx + S(21), cy)]
    pygame.draw.lines(screen, color, False, pts, 3)
    pygame.draw.circle(screen, color, (cx - S(18), cy), 2)
    pygame.draw.circle(screen, color, (cx + S(21), cy), 2)


def draw_system_symbol(screen, cx, cy, color):
    pygame.draw.rect(screen, color, (cx - S(11), cy - S(11), S(22), S(22)), 2, border_radius=3)
    pygame.draw.rect(screen, color, (cx - S(5), cy - S(5), S(10), S(10)), 2, border_radius=2)
    for dx, dy in ((0, -16), (0, 16), (-16, 0), (16, 0), (-12, -12), (12, -12), (-12, 12), (12, 12)):
        pygame.draw.line(screen, color, (cx + S(dx), cy + S(dy)), (cx + S(dx) // 2, cy + S(dy) // 2), 2)


def draw_logs_symbol(screen, cx, cy, color):
    pygame.draw.rect(screen, color, (cx - S(12), cy - S(15), S(24), S(30)), 2, border_radius=3)
    pygame.draw.line(screen, color, (cx - S(7), cy - S(7)), (cx + S(7), cy - S(7)), 2)
    pygame.draw.line(screen, color, (cx - S(7), cy), (cx + S(7), cy), 2)
    pygame.draw.line(screen, color, (cx - S(7), cy + S(7)), (cx + S(3), cy + S(7)), 2)


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


def draw_pulse_strip(screen, t):
    strip = pygame.Rect(S(14), S(12), WIDTH - S(28), S(14))
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


def draw_status_panel(screen, rect, fonts, data, now):
    neon_box(screen, rect, VIOLET, pulse=now + 0.8)
    title = text_surf(fonts["panel_title"], "SYSTEM STATS", TEXT)
    screen.blit(title, (rect.x + S(12), rect.y + S(10)))

    temp_f = c_to_f(data["temp"])
    labels = [
        ("STORE", data["store"], VIOLET),
        ("TEMP", temp_f, VIOLET),
    ]
    col_w = (rect.w - S(24)) // 3
    for i, (name, val, color) in enumerate(labels):
        x = rect.x + S(12) + i * col_w
        screen.blit(text_surf(fonts["sm"], name, MUTED), (x, rect.y + S(48)))
        screen.blit(text_surf(fonts["stat_val"], f"{int(val)}%" if name != "TEMP" else f"{int(val)}F", color), (x, rect.y + S(86)))
        draw_metric_bar(screen, x, rect.y + S(114), val if name != "TEMP" else ((val - 86) * 1.2), color)
        if i < 2:
            pygame.draw.line(screen, (36, 43, 73), (x + col_w - S(8), rect.y + S(38)), (x + col_w - S(8), rect.bottom - S(16)), 1)

    up_x = rect.x + S(12) + 2 * col_w
    screen.blit(text_surf(fonts["sm"], "UPTIME", MUTED), (up_x, rect.y + S(48)))
    screen.blit(text_surf(fonts["stat_val"], data["uptime"], VIOLET), (up_x, rect.y + S(92)))


def draw_cpu_mem_panel(screen, rect, fonts, data, now):
    neon_box(screen, rect, CYAN, pulse=now + 1.7)
    screen.blit(text_surf(fonts["panel_title"], "SYSTEM LOAD", TEXT), (rect.x + S(12), rect.y + S(10)))

    col_w = (rect.w - S(24)) // 2
    items = [("CPU", data["cpu"], CYAN), ("MEM", data["mem"], CYAN)]
    for i, (name, val, color) in enumerate(items):
        x = rect.x + S(12) + i * col_w
        label = text_surf(fonts["sm"], name, MUTED)
        screen.blit(label, (x, rect.y + S(48)))
        screen.blit(text_surf(fonts["load_val"], f"{int(val)}%", color), (x + label.get_width() + S(12), rect.y + S(40)))
        draw_metric_bar(screen, x, rect.y + S(90), val, color)
        if i == 0:
            pygame.draw.line(screen, (36, 43, 73), (x + col_w - S(8), rect.y + S(38)), (x + col_w - S(8), rect.bottom - S(16)), 1)


def draw_placeholder_view(screen, rect, fonts, title, now, color):
    neon_box(screen, rect, color, pulse=now + 2.5)
    draw_scanline_shimmer(screen, rect, now)
    screen.blit(text_surf(fonts["panel_title"], title, TEXT), (rect.x + S(18), rect.y + S(18)))
    screen.blit(text_surf(fonts["sm"], "Module stub. Tap HOME to return.", MUTED), (rect.x + S(18), rect.y + S(60)))


def draw_flashlight_overlay(screen, rect):
    pygame.draw.rect(screen, FLASHLIGHT, rect, border_radius=8)


def draw_main(screen, fonts, data, selected, current_view, light_on, now):
    screen.fill(BG)

    outer = pygame.Rect(S(6), S(6), WIDTH - S(12), HEIGHT - S(12))
    neon_box(screen, outer, (24, 94, 120), fill=(2, 4, 12), radius=10, pulse=now)

    # Top bar
    top = pygame.Rect(S(14), S(20), WIDTH - S(28), S(34))
    pygame.draw.line(screen, (20, 35, 60), (top.x, top.bottom), (top.right, top.bottom), 1)
    screen.blit(text_surf(fonts["top"], "KAGE // LVL 27", PINK), (top.x + S(10), top.y + S(8)))
    live = text_surf(fonts["top"], "LIVE INTEL", PINK)
    screen.blit(live, (WIDTH // 2 - live.get_width() // 2, top.y + S(8)))
    clock_text = text_surf(fonts["top"], data["clock"], PINK)
    screen.blit(clock_text, (top.right - S(122), top.y + S(8)))
    draw_last_update(screen, fonts, data, top, now)

    # Left menu
    left = pygame.Rect(S(14), S(54), S(170), HEIGHT - S(68))
    menu_items = ["WIFI", "BLUETOOTH", "HOME", "CONFIG", "LIGHT"]
    menu_colors = [PINK, CYAN, VIOLET, VIOLET, WHITE]
    tile_h = S(78)
    tile_gap = S(8)
    for i, name in enumerate(menu_items):
        r = pygame.Rect(left.x, left.y + i * (tile_h + tile_gap), left.w, tile_h)
        col = menu_colors[i]
        active = (i == selected and i != 4) or (i == 4 and light_on)
        if active and i == 4:
            fill = WHITE
        else:
            fill = scale_color(col, 0.78) if active else (5, 8, 20)
        neon_box(screen, r, col, fill=fill, pulse=now + i * 0.4)
        if active:
            draw_active_button_shimmer(screen, r, now)
        text_col = (10, 12, 18) if active else TEXT
        screen.blit(text_surf(fonts["menu"], name, text_col), (r.x + S(18), r.y + S(28)))

    # Right content
    rx = left.right + S(10)
    rw = WIDTH - rx - S(14)
    content_rect = pygame.Rect(rx, S(54), rw, HEIGHT - S(68))

    if current_view != "home":
        draw_placeholder_view(screen, content_rect, fonts, current_view.upper(), now, CYAN if current_view == "bluetooth" else PINK)
        if light_on:
            draw_flashlight_overlay(screen, content_rect)
        draw_pulse_strip(screen, now)
        return

    panel_gap = S(10)
    wifi = pygame.Rect(rx, S(54), rw, S(130))
    wifi_scanning = data.get("wifi_scanning", False)
    ble_scanning = data.get("ble_scanning", False)
    split_x = wifi.x + (wifi.w // 2)

    neon_box(screen, wifi, PINK, pulse=now + 0.2)
    draw_wire_grid(screen, wifi.inflate(-S(8), -S(10)), PINK)
    draw_scanline_shimmer(screen, wifi, now)
    pygame.draw.line(screen, (90, 20, 60), (split_x, wifi.y + S(20)), (split_x, wifi.bottom - S(20)), 2)

    # Left half — WIFI
    if wifi_scanning:
        left_half = pygame.Rect(wifi.x + 2, wifi.y + 2, split_x - wifi.x - 3, wifi.h - 4)
        pygame.draw.rect(screen, PINK, left_half, border_radius=S(6))
        screen.blit(text_surf(fonts["panel_title"], "WIFI FOUND", BG), (wifi.x + S(18), wifi.y + S(14)))
        blink = int(now * 4) % 2 == 0
        screen.blit(text_surf(fonts["sm"], "● SCANNING" if blink else "  SCANNING", BG), (wifi.x + S(18), wifi.y + S(60)))
    else:
        screen.blit(text_surf(fonts["panel_title"], "WIFI FOUND", TEXT), (wifi.x + S(18), wifi.y + S(14)))
        screen.blit(text_surf(fonts["wifi_num"], str(data["wifi"]), PINK), (wifi.x + S(18), wifi.y + S(54)))

    # Right half — BLE
    if ble_scanning:
        right_half = pygame.Rect(split_x + 1, wifi.y + 2, wifi.right - split_x - 3, wifi.h - 4)
        pygame.draw.rect(screen, CYAN, right_half, border_radius=S(6))
        screen.blit(text_surf(fonts["panel_title"], "BLE FOUND", BG), (split_x + S(18), wifi.y + S(14)))
        blink = int(now * 4) % 2 == 0
        screen.blit(text_surf(fonts["sm"], "● SCANNING" if blink else "  SCANNING", BG), (split_x + S(18), wifi.y + S(60)))
    else:
        screen.blit(text_surf(fonts["panel_title"], "BLE FOUND", TEXT), (split_x + S(18), wifi.y + S(14)))
        screen.blit(text_surf(fonts["wifi_num"], str(data["ble"]), CYAN), (split_x + S(18), wifi.y + S(54)))

    cpu_mem = pygame.Rect(rx, wifi.bottom + panel_gap, rw, S(108))
    draw_cpu_mem_panel(screen, cpu_mem, fonts, data, now)
    draw_scanline_shimmer(screen, cpu_mem, now + 0.6)

    stats = pygame.Rect(rx, cpu_mem.bottom + panel_gap, rw, content_rect.bottom - (cpu_mem.bottom + panel_gap))
    draw_status_panel(screen, stats, fonts, data, now)
    draw_scanline_shimmer(screen, stats, now + 1.1)

    if light_on:
        draw_flashlight_overlay(screen, content_rect)

    draw_pulse_strip(screen, now)


def make_fonts():
    # Fall back to defaults automatically; this still requires pygame font support.
    def fs(n):
        return max(8, S(n))
    return {
        "sm": pygame.font.SysFont("dejavusansmono", fs(20), bold=True),
        "top": pygame.font.SysFont("dejavusansmono", fs(17), bold=True),
        "tiny": pygame.font.SysFont("dejavusansmono", fs(12), bold=True),
        "menu": pygame.font.SysFont("dejavusansmono", fs(27), bold=True),
        "panel_title": pygame.font.SysFont("dejavusansmono", fs(26), bold=True),
        "lg": pygame.font.SysFont("dejavusansmono", fs(54), bold=True),
        "stat_val": pygame.font.SysFont("dejavusansmono", fs(27), bold=True),
        "load_val": pygame.font.SysFont("dejavusansmono", fs(41), bold=True),
        "wifi_num": pygame.font.SysFont("dejavusansmono", fs(52), bold=True),
    }


def update_data(data, cache, start_time, now):
    intervals = CONFIG["refresh_intervals"]
    scan_intervals = CONFIG["scan_intervals"]

    if now - cache.get("load_refresh_at", -intervals["load_seconds"]) >= intervals["load_seconds"]:
        cpu = read_cpu_percent(cache)
        mem = read_mem_percent()
        if cpu is not None:
            data["cpu"] = cpu
        if mem is not None:
            data["mem"] = mem
        cache["load_refresh_at"] = now

    if now - cache.get("stats_refresh_at", -intervals["stats_seconds"]) >= intervals["stats_seconds"]:
        store = read_storage_percent()
        temp_c = read_temp_c()
        if store is not None:
            data["store"] = store
        if temp_c is not None:
            data["temp"] = clamp(temp_c, -40.0, 140.0)
        cache["stats_refresh_at"] = now

    if now - cache.get("wifi_refresh_at", -scan_intervals["wifi_seconds"]) >= scan_intervals["wifi_seconds"]:
        cache["wifi_scan_started"] = now
        data["wifi"] = clamp(read_wifi_count(), 0, 999)
        cache["wifi_refresh_at"] = now

    if now - cache.get("ble_refresh_at", -scan_intervals["ble_seconds"]) >= scan_intervals["ble_seconds"]:
        cache["ble_scan_started"] = now
        data["ble"] = clamp(read_ble_count(), 0, 999)
        cache["ble_refresh_at"] = now

    data["wifi_scanning"] = (now - cache.get("wifi_scan_started", -(SCAN_ANIM_SECS + 1))) < SCAN_ANIM_SECS
    data["ble_scanning"] = (now - cache.get("ble_scan_started", -(SCAN_ANIM_SECS + 1))) < SCAN_ANIM_SECS

    uptime = read_uptime_str()

    data["clock"] = time.strftime("%H:%M")
    data["last_update"] = time.strftime("%H:%M:%S")
    if uptime is not None:
        data["uptime"] = uptime
    else:
        elapsed = int(time.time() - start_time)
        hh = elapsed // 3600
        mm = (elapsed % 3600) // 60
        data["uptime"] = f"{hh:01d}:{mm:02d}"


def main():
    init_pygame_or_die()

    global WIDTH, HEIGHT, SCALE
    info = pygame.display.Info()
    WIDTH = info.current_w
    HEIGHT = info.current_h
    SCALE = min(WIDTH / BASE_W, HEIGHT / BASE_H)
    print(f"[startup] display: {WIDTH}x{HEIGHT}  scale: {SCALE:.3f}")

    pygame.display.set_caption("pip-pi live intel")
    pygame.mouse.set_visible(False)

    flags = pygame.FULLSCREEN if "--fullscreen" in set(sys.argv[1:]) else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    clock = pygame.time.Clock()

    fonts = make_fonts()
    click_sound = init_click_sound()
    selected = 2
    current_view = "home"
    light_on = False
    start = time.time()
    data = {
        "wifi": 0,
        "ble": 0,
        "cpu": 0,
        "mem": 0,
        "store": 0,
        "temp": 0,
        "clock": "00:00",
        "last_update": "--:--:--",
        "uptime": "0:00:00",
        "wifi_scanning": False,
        "ble_scanning": False,
    }
    # Stagger BLE scan 30s after WiFi (WiFi fires immediately at t=0).
    _wifi_secs = CONFIG["scan_intervals"]["wifi_seconds"]
    _ble_secs = CONFIG["scan_intervals"]["ble_seconds"]
    cache = {
        "wifi_refresh_at": -_wifi_secs,
        "ble_refresh_at": -_ble_secs + 30.0,
    }
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
                menu_x0 = S(14)
                menu_x1 = S(14) + S(170)
                if menu_x0 <= mx <= menu_x1:
                    tile_h = S(78)
                    tile_gap = S(8)
                    start_y = S(54)
                    for i in range(5):
                        y = start_y + i * (tile_h + tile_gap)
                        if y <= my <= y + tile_h:
                            if i == 4:
                                light_on = not light_on
                            else:
                                light_on = False
                                selected = i
                                if i == 2:
                                    current_view = "home"
                                elif i == 0:
                                    current_view = "wifi"
                                elif i == 1:
                                    current_view = "bluetooth"
                                elif i == 3:
                                    current_view = "config"
                            break

        now = time.time()
        update_data(data, cache, start, now)

        draw_main(screen, fonts, data, selected, current_view, light_on, now)
        draw_ripples(screen, ripples, now)

        # Keep only active ripple effects.
        ripples = [rp for rp in ripples if (now - rp["born"]) < RIPPLE_LIFE]
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
