def panel_bluetooth(screen, rect, fonts, data, now, *, neon_box, draw_scanline_shimmer, text_surf, draw_signal_list_rows, S, colors):
    CYAN = colors["CYAN"]
    PINK = colors["PINK"]
    BG = colors["BG"]
    MUTED = colors["MUTED"]

    devices = data.get("ble_devices", [])
    scanning = data.get("ble_scanning", False)

    neon_box(screen, rect, CYAN, pulse=now + 0.6)
    draw_scanline_shimmer(screen, rect, now)

    title = "BLUETOOTH" + (" ● SCANNING" if scanning and int(now * 4) % 2 == 0 else " ■ SCANNING" if scanning else "")
    title_color = CYAN if not scanning else BG if int(now * 4) % 2 == 0 else CYAN
    screen.blit(text_surf(fonts["panel_title"], title, title_color), (rect.x + S(18), rect.y + S(12)))

    if not devices:
        msg = "● SCANNING..." if scanning else "NO DEVICES FOUND"
        screen.blit(text_surf(fonts["sm"], msg, MUTED), (rect.x + S(18), rect.y + S(56)))
        return

    draw_signal_list_rows(
        screen=screen,
        rect=rect,
        fonts=fonts,
        entries=devices,
        get_name=lambda e: e[0],
        get_dbm=lambda e: e[2] if len(e) >= 3 else None,
        get_bar_color=lambda rssi: MUTED if rssi is None else (CYAN if rssi >= -70 else PINK if rssi >= -85 else MUTED),
    )
