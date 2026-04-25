def panel_wifi(screen, rect, fonts, data, now, *, neon_box, draw_scanline_shimmer, text_surf, draw_signal_list_rows, S, colors):
    PINK = colors["PINK"]
    CYAN = colors["CYAN"]
    BG = colors["BG"]
    MUTED = colors["MUTED"]

    networks = data.get("wifi_networks", [])
    scanning = data.get("wifi_scanning", False)

    neon_box(screen, rect, PINK, pulse=now + 0.2)
    draw_scanline_shimmer(screen, rect, now)

    title = "WIFI" + (" ● SCANNING" if scanning and int(now * 4) % 2 == 0 else " ■ SCANNING" if scanning else "")
    title_color = PINK if not scanning else BG if int(now * 4) % 2 == 0 else PINK
    screen.blit(text_surf(fonts["panel_title"], title, title_color), (rect.x + S(18), rect.y + S(12)))

    if not networks:
        msg = "● SCANNING..." if scanning else "NO NETWORKS FOUND"
        screen.blit(text_surf(fonts["sm"], msg, MUTED), (rect.x + S(18), rect.y + S(56)))
        return

    draw_signal_list_rows(
        screen=screen,
        rect=rect,
        fonts=fonts,
        entries=networks,
        get_name=lambda e: e[0],
        get_dbm=lambda e: e[1],
        get_bar_color=lambda dbm: PINK if dbm >= -65 else CYAN if dbm >= -75 else MUTED,
    )
