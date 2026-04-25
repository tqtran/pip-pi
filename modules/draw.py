import math

import pygame
from modules.panels.panel_bluetooth import panel_bluetooth
from modules.panels.panel_config import panel_config
from modules.panels.panel_cpu_mem import panel_cpu_mem
from modules.panels.panel_home import panel_home
from modules.panels.panel_wifi import panel_wifi

BASE_W, BASE_H = 720, 480
WIDTH, HEIGHT = BASE_W, BASE_H
SCALE = 1.0

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
FLASHLIGHT = (255, 255, 255)


def configure_layout(width, height, scale):
    global WIDTH, HEIGHT, SCALE
    WIDTH = int(width)
    HEIGHT = int(height)
    SCALE = float(scale)


def S(n):
    return int(round(n * SCALE))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def c_to_f(celsius):
    return (celsius * 9.0 / 5.0) + 32.0


def scale_color(color, factor):
    return tuple(clamp(int(c * factor), 0, 255) for c in color)


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


def draw_metric_bar(screen, x, y, value, color, blocks=8):
    on = int(round(clamp(value, 0, 100) / 100 * blocks))
    w, h, gap = max(1, S(10)), max(1, S(12)), max(1, S(2))
    for i in range(blocks):
        c = color if i < on else (28, 34, 62)
        pygame.draw.rect(screen, c, (x + i * (w + gap), y, w, h), border_radius=2)


def draw_scanline_shimmer(screen, rect, now):
    overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bright_y = int((now * 56) % max(1, rect.h))
    line_h = max(2, S(2))
    y = max(0, min(rect.h - line_h, bright_y))
    pygame.draw.rect(overlay, (255, 255, 255, 64), (0, y, rect.w, line_h))
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


def draw_pulse_strip(screen, t):
    strip = pygame.Rect(S(14), S(12), WIDTH - S(28), S(7))
    segs = 40
    gap = 0
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




def signal_bars(dbm, floor_dbm=-100, span_dbm=60):
    if dbm is None:
        return "░" * 5
    frac = clamp((dbm - floor_dbm) / float(span_dbm), 0.0, 1.0)
    filled = int(round(frac * 5))
    return "".join("█" if i < filled else "░" for i in range(5))


def draw_signal_list_rows(screen, rect, fonts, entries, get_name, get_dbm, get_bar_color):
    row_h = S(56)
    max_rows = max(1, (rect.h - S(48)) // row_h)
    visible = entries[:max_rows]

    dbm_col_w = fonts["list_item"].size("-100dBm")[0] + S(8)
    bar_col_w = fonts["list_item"].size("█" * 5)[0] + S(6)
    name_max_w = rect.w - S(24) - bar_col_w - dbm_col_w

    for idx, entry in enumerate(visible):
        dbm = get_dbm(entry)
        y = rect.y + S(48) + idx * row_h
        bars = signal_bars(dbm)
        bc = get_bar_color(dbm)
        bx = rect.x + S(12)
        screen.blit(text_surf(fonts["list_item"], bars, bc), (bx, y))

        name = str(get_name(entry))
        name_surf = fonts["list_item"].render(f" {name}", True, TEXT)
        if name_surf.get_width() > name_max_w:
            name_surf = name_surf.subsurface((0, 0, name_max_w, name_surf.get_height()))
        screen.blit(name_surf, (bx + bar_col_w, y))

        dbm_str = f"{int(dbm)}dBm" if dbm is not None else ""
        screen.blit(text_surf(fonts["list_item"], dbm_str, MUTED), (rect.right - dbm_col_w, y))

    if len(entries) > max_rows:
        screen.blit(text_surf(fonts["list_item"], f"+{len(entries) - max_rows} more", MUTED), (rect.x + S(18), rect.bottom - S(20)))


def draw_placeholder_view(screen, rect, fonts, title, now, color):
    neon_box(screen, rect, color, pulse=now + 2.5)
    draw_scanline_shimmer(screen, rect, now)
    screen.blit(text_surf(fonts["panel_title"], title, TEXT), (rect.x + S(18), rect.y + S(18)))
    screen.blit(text_surf(fonts["sm"], "Module stub. Tap HOME to return.", MUTED), (rect.x + S(18), rect.y + S(60)))


def draw_flashlight_overlay(screen, rect):
    pygame.draw.rect(screen, FLASHLIGHT, rect, border_radius=8)


def _fit_font_by_width(fonts, text, max_width, keys):
    for key in keys:
        font = fonts[key]
        if font.size(text)[0] <= max_width:
            return font
    return fonts[keys[-1]]


def draw_uptime_clock_row(screen, rect, fonts, data, now, *, neon_box, text_surf, S, colors):
    PINK = colors["PINK"]
    VIOLET = colors["VIOLET"]
    MUTED = colors["MUTED"]

    neon_box(screen, rect, VIOLET, pulse=now + 0.4)
    split_x = rect.x + int(rect.w * 0.38)
    pygame.draw.line(screen, (36, 43, 73), (split_x, rect.y + S(10)), (split_x, rect.bottom - S(10)), 1)

    up_label = text_surf(fonts["sm"], "UPTIME", MUTED)
    up_value = text_surf(fonts["panel_title"], data["uptime"], VIOLET)
    up_value_y = rect.y + S(9)
    up_label_y = up_value_y + up_value.get_height() + S(2)
    screen.blit(up_value, (rect.x + S(16), up_value_y))
    screen.blit(up_label, (rect.x + S(16), up_label_y))

    clock_font = _fit_font_by_width(fonts, data["clock"], rect.right - split_x - S(24), ["lg", "wifi_num", "home_stat", "load_line"])
    clock_text = text_surf(clock_font, data["clock"], PINK)
    clock_y = rect.centery - clock_text.get_height() // 2
    clock_x = rect.right - S(16) - clock_text.get_width()
    screen.blit(clock_text, (clock_x, clock_y))


def draw_main(screen, fonts, data, selected, current_view, light_on, now, config):
    screen.fill(BG)

    outer = pygame.Rect(S(6), S(6), WIDTH - S(12), HEIGHT - S(12))
    neon_box(screen, outer, (24, 94, 120), fill=(2, 4, 12), radius=10, pulse=now)

    top = pygame.Rect(S(14), S(20), WIDTH - S(28), S(34))
    pygame.draw.line(screen, (20, 35, 60), (top.x, top.bottom), (top.right, top.bottom), 1)

    # --- status bar ---

    status_msg = data.get("status_msg", "")
    status_at  = data.get("status_msg_at", 0.0)
    _STATUS_TTL = 6.0  # seconds before message fades
    if status_msg:
        age = now - status_at
        if age < _STATUS_TTL:
            alpha = int(255 * max(0.0, 1.0 - age / _STATUS_TTL))
            msg_surf = fonts["tiny"].render(status_msg, True, CYAN)
            msg_surf.set_alpha(alpha)
            msg_x = top.x + S(6)
            msg_y = top.y + (top.h - msg_surf.get_height()) // 2
            screen.blit(msg_surf, (msg_x, msg_y))
        else:
            data["status_msg"] = ""

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
        menu_font = _fit_font_by_width(fonts, name, r.w - S(24), ["menu", "panel_title", "sm", "top"])
        menu_text = text_surf(menu_font, name, text_col)
        menu_pos = (r.x + S(18), r.centery - menu_text.get_height() // 2)
        screen.blit(menu_text, menu_pos)

    rx = left.right + S(10)
    rw = WIDTH - rx - S(14)
    content_rect = pygame.Rect(rx, S(54), rw, HEIGHT - S(68))

    if current_view != "home":
        if current_view == "wifi":
            panel_wifi(
                screen,
                content_rect,
                fonts,
                data,
                now,
                neon_box=neon_box,
                draw_scanline_shimmer=draw_scanline_shimmer,
                text_surf=text_surf,
                draw_signal_list_rows=draw_signal_list_rows,
                S=S,
                colors={"PINK": PINK, "CYAN": CYAN, "BG": BG, "MUTED": MUTED, "TEXT": TEXT},
            )
        elif current_view == "bluetooth":
            panel_bluetooth(
                screen,
                content_rect,
                fonts,
                data,
                now,
                neon_box=neon_box,
                draw_scanline_shimmer=draw_scanline_shimmer,
                text_surf=text_surf,
                draw_signal_list_rows=draw_signal_list_rows,
                S=S,
                colors={"CYAN": CYAN, "PINK": PINK, "BG": BG, "MUTED": MUTED},
            )
        elif current_view == "config":
            panel_config(
                screen,
                content_rect,
                fonts,
                data,
                now,
                config,
                neon_box=neon_box,
                text_surf=text_surf,
                S=S,
                colors={"PINK": PINK, "CYAN": CYAN, "MUTED": MUTED, "TEXT": TEXT},
            )
        else:
            draw_placeholder_view(screen, content_rect, fonts, current_view.upper(), now, VIOLET)
        if light_on:
            draw_flashlight_overlay(screen, content_rect)
        draw_pulse_strip(screen, now)
        return

    panel_gap = S(10)
    total_h = content_rect.h
    usable_h = max(S(120), total_h - (panel_gap * 2))
    uptime_h = int(usable_h * 0.18)
    wifi_h = int(usable_h * 0.40)
    metrics_h = usable_h - uptime_h - wifi_h

    uptime_row = pygame.Rect(rx, content_rect.y, rw, uptime_h)
    draw_uptime_clock_row(
        screen,
        uptime_row,
        fonts,
        data,
        now,
        neon_box=neon_box,
        text_surf=text_surf,
        S=S,
        colors={"PINK": PINK, "VIOLET": VIOLET, "MUTED": MUTED},
    )

    wifi = pygame.Rect(rx, uptime_row.bottom + panel_gap, rw, wifi_h)

    panel_home(
        screen,
        wifi,
        fonts,
        data,
        now,
        config,
        neon_box=neon_box,
        draw_wire_grid=draw_wire_grid,
        draw_scanline_shimmer=draw_scanline_shimmer,
        text_surf=text_surf,
        scale_color=scale_color,
        S=S,
        colors={"PINK": PINK, "CYAN": CYAN, "BG": BG},
    )

    cpu_mem = pygame.Rect(rx, wifi.bottom + panel_gap, rw, metrics_h)
    temp_f = c_to_f(data["temp"])
    metric_items = [
        ("CPU", data["cpu"], VIOLET, "%"),
        ("MEM", data["mem"], VIOLET, "%"),
        ("STORE", data["store"], VIOLET, "%"),
        ("TEMP", temp_f, VIOLET, "F"),
    ]
    panel_cpu_mem(
        screen,
        cpu_mem,
        fonts,
        data,
        now,
        neon_box=neon_box,
        text_surf=text_surf,
        draw_metric_bar=draw_metric_bar,
        S=S,
        colors={"CYAN": VIOLET},
        items=metric_items,
    )
    draw_scanline_shimmer(screen, cpu_mem, now + 0.6)

    if light_on:
        draw_flashlight_overlay(screen, content_rect)

    draw_pulse_strip(screen, now)


def draw_frame(screen, fonts, data, selected, current_view, light_on, now, config, ripples):
    draw_main(screen, fonts, data, selected, current_view, light_on, now, config)
    draw_ripples(screen, ripples, now)


def make_fonts():
    def fs(n):
        return max(8, S(n))

    font_name = "tahoma"

    return {
        "sm": pygame.font.SysFont(font_name, fs(20), bold=True),
        "top": pygame.font.SysFont(font_name, fs(17), bold=True),
        "clock": pygame.font.SysFont(font_name, fs(30), bold=True),
        "tiny": pygame.font.SysFont(font_name, fs(12), bold=True),
        "list_item": pygame.font.SysFont(font_name, fs(24), bold=True),
        "menu": pygame.font.SysFont(font_name, fs(25), bold=True),
        "panel_title": pygame.font.SysFont(font_name, fs(26), bold=True),
        "home_stat": pygame.font.SysFont(font_name, fs(40), bold=True),
        "home_stat_big": pygame.font.SysFont(font_name, fs(48), bold=True),
        "lg": pygame.font.SysFont(font_name, fs(54), bold=True),
        "stat_val": pygame.font.SysFont(font_name, fs(27), bold=True),
        "load_val": pygame.font.SysFont(font_name, fs(41), bold=True),
        "load_val_big": pygame.font.SysFont(font_name, fs(49), bold=True),
        "load_line": pygame.font.SysFont(font_name, fs(33), bold=True),
        "load_line_big": pygame.font.SysFont(font_name, fs(40), bold=True),
        "wifi_num": pygame.font.SysFont(font_name, fs(52), bold=True),
    }
