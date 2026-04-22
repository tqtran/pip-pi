#!/usr/bin/env python3
"""
pip-pi dashboard prototype.

Reference-inspired neon layout using rectangles, lines, and text only.
No image assets required.
"""

import math
import random
import sys
import time

import pygame

WIDTH, HEIGHT = 720, 480
FPS = 30
DATA_HZ = 4.0
RIPPLE_LIFE = 0.45

BG = (4, 6, 16)
PANEL_BG = (8, 10, 24)
TEXT = (224, 230, 238)
MUTED = (116, 136, 158)
PINK = (255, 14, 142)
CYAN = (0, 197, 255)
VIOLET = (122, 56, 255)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


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
    for r, th in ((52, 11), (34, 9), (18, 7)):
        pygame.draw.arc(screen, color, (cx - r, cy - r, 2 * r, 2 * r), math.radians(215), math.radians(325), th)
    pygame.draw.circle(screen, color, (cx, cy), 10)


def draw_bluetooth_symbol(screen, cx, cy, color):
    pygame.draw.line(screen, color, (cx, cy - 44), (cx, cy + 44), 5)
    pygame.draw.line(screen, color, (cx, cy - 44), (cx + 28, cy - 14), 5)
    pygame.draw.line(screen, color, (cx, cy + 44), (cx + 28, cy + 14), 5)
    pygame.draw.line(screen, color, (cx - 2, cy), (cx + 28, cy - 14), 5)
    pygame.draw.line(screen, color, (cx - 2, cy), (cx + 28, cy + 14), 5)


def draw_bottom_pulse_strip(screen, t):
    strip = pygame.Rect(14, HEIGHT - 22, WIDTH - 28, 14)
    segs = 40
    gap = 2
    seg_w = (strip.w - (segs - 1) * gap) // segs
    for i in range(segs):
        f = i / max(1, segs - 1)
        base = (
            int(PINK[0] * (1.0 - f) + CYAN[0] * f),
            int(PINK[1] * (1.0 - f) + CYAN[1] * f),
            int(PINK[2] * (1.0 - f) + CYAN[2] * f),
        )
        pulse = 0.62 + 0.38 * (0.5 + 0.5 * math.sin(t * 4.2 + i * 0.45))
        c = (int(base[0] * pulse), int(base[1] * pulse), int(base[2] * pulse))
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
        color = rp["color"]
        for k in range(3):
            r = base_r + k * 14
            a = max(0, alpha - k * 35)
            if a > 0:
                pygame.draw.circle(overlay, (color[0], color[1], color[2], a), (rp["x"], rp["y"]), r, 2)

    screen.blit(overlay, (0, 0))


def draw_status_panel(screen, rect, fonts, data):
    neon_box(screen, rect, VIOLET)
    title = text_surf(fonts["md"], "SYSTEM STATS", TEXT)
    screen.blit(title, (rect.x + 12, rect.y + 10))

    labels = [
        ("CPU", data["cpu"], VIOLET),
        ("MEM", data["mem"], VIOLET),
        ("STORE", data["store"], VIOLET),
        ("TEMP", data["temp"], VIOLET),
    ]
    col_w = (rect.w - 24) // 5
    for i, (name, val, color) in enumerate(labels):
        x = rect.x + 12 + i * col_w
        screen.blit(text_surf(fonts["sm"], name, MUTED), (x, rect.y + 48))
        screen.blit(text_surf(fonts["lg"], f"{int(val)}%" if name != "TEMP" else f"{int(val)}C", color), (x, rect.y + 74))
        draw_metric_bar(screen, x, rect.y + 114, val if name != "TEMP" else (val - 30) * 2, color)
        if i < 4:
            pygame.draw.line(screen, (36, 43, 73), (x + col_w - 8, rect.y + 38), (x + col_w - 8, rect.bottom - 16), 1)

    up_x = rect.x + 12 + 4 * col_w
    screen.blit(text_surf(fonts["sm"], "UPTIME", MUTED), (up_x, rect.y + 48))
    screen.blit(text_surf(fonts["lg"], data["uptime"], VIOLET), (up_x, rect.y + 82))


def draw_main(screen, fonts, data, selected, now):
    screen.fill(BG)

    outer = pygame.Rect(6, 6, WIDTH - 12, HEIGHT - 12)
    neon_box(screen, outer, (24, 94, 120), fill=(2, 4, 12), radius=10)

    # Top bar
    top = pygame.Rect(14, 14, WIDTH - 28, 34)
    pygame.draw.line(screen, (20, 35, 60), (top.x, top.bottom), (top.right, top.bottom), 1)
    screen.blit(text_surf(fonts["md"], "KAGE // LVL 27", PINK), (top.x + 10, top.y + 4))
    live = text_surf(fonts["md"], "LIVE INTEL", PINK)
    screen.blit(live, (WIDTH // 2 - live.get_width() // 2, top.y + 4))
    screen.blit(text_surf(fonts["md"], data["clock"], PINK), (top.right - 128, top.y + 4))
    screen.blit(text_surf(fonts["md"], f"{data['battery']}%", CYAN), (top.right - 54, top.y + 4))

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
        screen.blit(text_surf(fonts["md"], name, TEXT), (r.x + 18, r.y + 25))

    # Right content
    rx = left.right + 10
    rw = WIDTH - rx - 14

    wifi = pygame.Rect(rx, 54, rw, 130)
    neon_box(screen, wifi, PINK)
    draw_wire_grid(screen, wifi.inflate(-8, -10), PINK)
    screen.blit(text_surf(fonts["md"], "WIFI FOUND", TEXT), (wifi.x + 18, wifi.y + 14))
    screen.blit(text_surf(fonts["xl"], str(data["wifi"]), PINK), (wifi.x + 18, wifi.y + 44))
    pygame.draw.line(screen, (90, 20, 60), (wifi.x + 210, wifi.y + 20), (wifi.x + 210, wifi.bottom - 20), 2)
    draw_wifi_symbol(screen, wifi.right - 180, wifi.y + 77, PINK)

    ble = pygame.Rect(rx, 194, rw, 108)
    neon_box(screen, ble, CYAN)
    draw_wire_grid(screen, ble.inflate(-8, -10), CYAN)
    screen.blit(text_surf(fonts["md"], "BLE FOUND", TEXT), (ble.x + 18, ble.y + 14))
    screen.blit(text_surf(fonts["lg"], str(data["ble"]), CYAN), (ble.x + 18, ble.y + 46))
    draw_bluetooth_symbol(screen, ble.right - 250, ble.y + 54, CYAN)

    stats = pygame.Rect(rx, 312, rw, HEIGHT - 326)
    draw_status_panel(screen, stats, fonts, data)

    draw_bottom_pulse_strip(screen, now)


def make_fonts():
    # Fall back to defaults automatically; this still requires pygame font support.
    return {
        "sm": pygame.font.SysFont("dejavusansmono", 20, bold=True),
        "md": pygame.font.SysFont("dejavusansmono", 34, bold=True),
        "lg": pygame.font.SysFont("dejavusansmono", 54, bold=True),
        "xl": pygame.font.SysFont("dejavusansmono", 104, bold=True),
    }


def update_data(data, start_time):
    t = time.time()
    phase = t * 0.8
    data["wifi"] = clamp(int(12 + 2 * math.sin(phase) + random.choice([0, 0, 1, -1])), 8, 16)
    data["ble"] = clamp(int(7 + 1 * math.sin(phase * 1.6) + random.choice([0, 0, 1, -1])), 3, 11)
    data["cpu"] = clamp(int(42 + 18 * abs(math.sin(phase * 1.2))), 10, 95)
    data["mem"] = clamp(int(56 + 8 * abs(math.sin(phase * 0.7 + 0.9))), 20, 95)
    data["store"] = clamp(int(45 + 2 * abs(math.sin(phase * 0.2))), 30, 85)
    data["temp"] = clamp(int(56 + 10 * abs(math.sin(phase * 1.4 + 0.3))), 38, 85)
    data["battery"] = clamp(int(87 - ((time.time() - start_time) / 120.0)), 20, 100)
    data["clock"] = time.strftime("%H:%M")
    elapsed = int(time.time() - start_time)
    hh = elapsed // 3600
    mm = (elapsed % 3600) // 60
    ss = elapsed % 60
    data["uptime"] = f"{hh:01d}:{mm:02d}:{ss:02d}"


def main():
    pygame.init()
    pygame.font.init()
    pygame.display.set_caption("pip-pi live intel")
    pygame.mouse.set_visible(False)

    flags = pygame.FULLSCREEN if "--fullscreen" in set(sys.argv[1:]) else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    clock = pygame.time.Clock()

    fonts = make_fonts()
    selected = 0
    start = time.time()
    last_data = 0.0
    data = {
        "wifi": 12,
        "ble": 7,
        "cpu": 45,
        "mem": 61,
        "store": 45,
        "temp": 62,
        "battery": 87,
        "clock": "00:00",
        "uptime": "0:00:00",
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
                ripple_color = CYAN if mx > WIDTH // 2 else PINK
                ripples.append({"x": mx, "y": my, "born": time.time(), "color": ripple_color})
                if 14 <= mx <= 184:
                    tile_h = 78
                    start_y = 54
                    for i in range(5):
                        y = start_y + i * (tile_h + 8)
                        if y <= my <= y + tile_h:
                            selected = i
                            break

        now = time.time()
        if now - last_data >= 1.0 / DATA_HZ:
            update_data(data, start)
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
