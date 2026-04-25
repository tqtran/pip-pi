import pygame


def _blit_clipped(screen, surf, pos, clip_rect):
    prev_clip = screen.get_clip()
    screen.set_clip(clip_rect)
    screen.blit(surf, pos)
    screen.set_clip(prev_clip)


def _fit_font(fonts, text, max_width, keys):
    for key in keys:
        font = fonts[key]
        if font.size(text)[0] <= max_width:
            return font
    return fonts[keys[-1]]


def _draw_label_value(screen, fonts, label, value, color, x, clip_rect, *, text_surf, y_center):
    gap = 8
    value_keys = ["home_stat_big", "home_stat", "panel_title", "menu", "sm"]
    chosen_label_surf = None
    chosen_value_surf = None

    for key in value_keys:
        value_font = fonts[key]
        target_px = max(8, int(value_font.get_height() * 0.5))
        label_font = pygame.font.SysFont("tahoma", target_px, bold=True)
        label_surf = text_surf(label_font, label, color)
        value_surf = text_surf(value_font, value, color)
        total_w = label_surf.get_width() + gap + value_surf.get_width()
        if total_w <= max(20, clip_rect.w - 6):
            chosen_label_surf = label_surf
            chosen_value_surf = value_surf
            break

    if chosen_label_surf is None or chosen_value_surf is None:
        value_font = fonts["sm"]
        target_px = max(8, int(value_font.get_height() * 0.5))
        label_font = pygame.font.SysFont("tahoma", target_px, bold=True)
        chosen_label_surf = text_surf(label_font, label, color)
        chosen_value_surf = text_surf(value_font, value, color)

    group_h = max(chosen_label_surf.get_height(), chosen_value_surf.get_height())
    y = y_center - group_h // 2

    # Keep label in column 1 and anchor value in column 3 (right third) of the half-panel.
    label_x = x
    value_col_x = clip_rect.x + int(clip_rect.w * 0.66)
    value_x = min(value_col_x, clip_rect.right - chosen_value_surf.get_width() - 4)
    value_x = max(label_x + chosen_label_surf.get_width() + gap, value_x)

    _blit_clipped(screen, chosen_label_surf, (label_x, y + (group_h - chosen_label_surf.get_height()) // 2), clip_rect)
    _blit_clipped(screen, chosen_value_surf, (value_x, y + (group_h - chosen_value_surf.get_height()) // 2), clip_rect)


def panel_home(screen, rect, fonts, data, now, config, *, neon_box, draw_wire_grid, draw_scanline_shimmer, text_surf, scale_color, S, colors):
    PINK = colors["PINK"]
    CYAN = colors["CYAN"]
    BG = colors["BG"]
    WHITE = (255, 255, 255)

    wifi_scanning = data.get("wifi_scanning", False)
    ble_scanning = data.get("ble_scanning", False)
    split_x = rect.x + (rect.w // 2)

    neon_box(screen, rect, PINK, pulse=now + 0.2)
    draw_wire_grid(screen, rect.inflate(-S(8), -S(10)), PINK)
    draw_scanline_shimmer(screen, rect, now)
    pygame.draw.line(screen, (90, 20, 60), (split_x, rect.y + S(20)), (split_x, rect.bottom - S(20)), 2)

    left_clip = pygame.Rect(rect.x + S(10), rect.y + S(8), split_x - rect.x - S(20), rect.h - S(24))
    right_clip = pygame.Rect(split_x + S(10), rect.y + S(8), rect.right - split_x - S(20), rect.h - S(24))

    left_text_x = rect.x + S(18)
    right_text_x = split_x + S(18)
    left_max_w = max(20, left_clip.w - S(8))
    right_max_w = max(20, right_clip.w - S(8))
    font_keys = ["home_stat_big", "home_stat", "panel_title", "menu", "sm"]

    if wifi_scanning:
        left_half = pygame.Rect(rect.x + 2, rect.y + 2, split_x - rect.x - 3, rect.h - 4)
        pygame.draw.rect(screen, PINK, left_half, border_radius=S(6))
        scan_text = "WIFI SCANNING ..."
        wifi_font = _fit_font(fonts, scan_text, left_max_w, font_keys)
        wifi_surf = text_surf(wifi_font, scan_text, WHITE)
        wifi_y = left_clip.y + S(12)
        _blit_clipped(screen, wifi_surf, (left_text_x, wifi_y), left_clip)
    else:
        wifi_label = "WIFI"
        wifi_value = str(int(data["wifi"]))
        _draw_label_value(
            screen,
            fonts,
            wifi_label,
            wifi_value,
            PINK,
            left_text_x,
            left_clip,
            text_surf=text_surf,
            y_center=left_clip.y + S(24),
        )

    if ble_scanning:
        right_half = pygame.Rect(split_x + 1, rect.y + 2, rect.right - split_x - 3, rect.h - 4)
        pygame.draw.rect(screen, CYAN, right_half, border_radius=S(6))
        scan_text = "BLE SCANNING ..."
        ble_font = _fit_font(fonts, scan_text, right_max_w, font_keys)
        ble_surf = text_surf(ble_font, scan_text, WHITE)
        ble_y = right_clip.y + S(12)
        _blit_clipped(screen, ble_surf, (right_text_x, ble_y), right_clip)
    else:
        ble_label = "BLE"
        ble_value = str(int(data["ble"]))
        _draw_label_value(
            screen,
            fonts,
            ble_label,
            ble_value,
            CYAN,
            right_text_x,
            right_clip,
            text_surf=text_surf,
            y_center=right_clip.y + S(24),
        )

    bar_h = max(2, S(4))
    bar_y = rect.bottom - bar_h - S(3)
    bar_margin = S(6)
    wifi_interval = config["scan_intervals"]["wifi_seconds"]
    ble_interval = config["scan_intervals"]["ble_seconds"]
    half_w = split_x - rect.x - bar_margin * 2
    if wifi_scanning:
        pygame.draw.rect(screen, BG, (rect.x + bar_margin, bar_y, half_w, bar_h), border_radius=2)
    else:
        frac = max(0.0, 1.0 - (now - data["wifi_refresh_at"]) / wifi_interval)
        pygame.draw.rect(screen, scale_color(PINK, 0.5), (rect.x + bar_margin, bar_y, half_w, bar_h), border_radius=2)
        pygame.draw.rect(screen, PINK, (rect.x + bar_margin, bar_y, int(half_w * frac), bar_h), border_radius=2)

    half_w2 = rect.right - split_x - bar_margin * 2
    if ble_scanning:
        pygame.draw.rect(screen, BG, (split_x + bar_margin, bar_y, half_w2, bar_h), border_radius=2)
    else:
        frac = max(0.0, 1.0 - (now - data["ble_refresh_at"]) / ble_interval)
        pygame.draw.rect(screen, scale_color(CYAN, 0.5), (split_x + bar_margin, bar_y, half_w2, bar_h), border_radius=2)
        pygame.draw.rect(screen, CYAN, (split_x + bar_margin, bar_y, int(half_w2 * frac), bar_h), border_radius=2)
