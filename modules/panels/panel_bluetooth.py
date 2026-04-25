import pygame


def _signal_quality(rssi):
    if rssi is None:
        return 0
    return max(0, min(100, int(round((rssi + 100) * (100.0 / 60.0)))))


def panel_bluetooth(screen, rect, fonts, data, now, *, neon_box, draw_scanline_shimmer, text_surf, draw_signal_list_rows, S, colors):
    CYAN = colors["CYAN"]
    PINK = colors["PINK"]
    BG = colors["BG"]
    MUTED = colors["MUTED"]
    TEXT = (224, 230, 238)

    devices = data.get("ble_devices", [])
    scanning = data.get("ble_scanning", False)

    neon_box(screen, rect, CYAN, pulse=now + 0.6)
    draw_scanline_shimmer(screen, rect, now)

    title = f"BLUETOOTH ({len(devices)} found)"
    screen.blit(text_surf(fonts["panel_title"], title, CYAN), (rect.x + S(18), rect.y + S(12)))

    if scanning:
        scan_color = BG if int(now * 4) % 2 == 0 else CYAN
        scan_surf = text_surf(fonts["sm"], "SCANNING", scan_color)
        screen.blit(scan_surf, (rect.right - S(18) - scan_surf.get_width(), rect.y + S(16)))

    if not devices:
        msg = "SCANNING..." if scanning else "NO DEVICES FOUND"
        screen.blit(text_surf(fonts["sm"], msg, MUTED), (rect.x + S(18), rect.y + S(56)))
        return

    row_h = S(56)
    row_top = rect.y + S(48)
    max_rows = max(1, (rect.h - S(52)) // row_h)
    visible = devices[:max_rows]

    bar_w = max(2, S(9))
    bar_h = max(2, S(14))
    bar_gap = max(1, S(2))
    bar_col_w = (bar_w * 5) + (bar_gap * 4) + S(6)
    dbm_col_w = fonts["list_item"].size("-100dBm")[0] + S(8)
    name_max_w = rect.w - S(24) - bar_col_w - dbm_col_w

    for idx, entry in enumerate(visible):
        name = str(entry[0])
        rssi = entry[2] if len(entry) >= 3 else None
        y = row_top + idx * row_h

        row_rect = pygame.Rect(rect.x + S(10), y, rect.w - S(20), row_h - S(2))
        pygame.draw.rect(screen, (12, 14, 30), row_rect, border_radius=S(4))
        if idx % 2 == 0:
            pygame.draw.rect(screen, (20, 34, 52), row_rect, 1, border_radius=S(4))

        bars_on = max(0, min(5, int(round((_signal_quality(rssi) / 100) * 5))))
        bc = CYAN if rssi is not None and rssi >= -70 else PINK if rssi is not None and rssi >= -85 else MUTED
        bx = rect.x + S(16)
        by = y + S(12)
        for bi in range(5):
            bar_color = bc if bi < bars_on else (28, 34, 62)
            pygame.draw.rect(screen, bar_color, (bx + bi * (bar_w + bar_gap), by, bar_w, bar_h), border_radius=2)

        name_surf = fonts["list_item"].render(f" {name}", True, TEXT)
        if name_surf.get_width() > name_max_w:
            name_surf = name_surf.subsurface((0, 0, name_max_w, name_surf.get_height()))
        screen.blit(name_surf, (bx + bar_col_w, y + S(4)))

        if rssi is not None:
            screen.blit(text_surf(fonts["list_item"], f"{int(rssi)}dBm", MUTED), (rect.right - dbm_col_w, y + S(4)))


