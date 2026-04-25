import pygame


def _signal_quality(dbm):
    if dbm is None:
        return 0
    return max(0, min(100, int(round((dbm + 100) * (100.0 / 60.0)))))


def wifi_click_action(mx, my, rect, data, S):
    networks = data.get("wifi_networks", [])
    selected_idx = data.get("wifi_selected_idx")

    if selected_idx is not None and 0 <= selected_idx < len(networks):
        back_rect = pygame.Rect(rect.x + S(18), rect.y + S(12), S(120), S(34))
        deauth_rect = pygame.Rect(rect.right - S(210), rect.bottom - S(66), S(190), S(44))
        if back_rect.collidepoint(mx, my):
            return "back", None
        if deauth_rect.collidepoint(mx, my):
            return "deauth", selected_idx
        return None, None

    row_h = S(56)
    row_top = rect.y + S(48)
    max_rows = max(1, (rect.h - S(52)) // row_h)
    visible_count = min(len(networks), max_rows)

    for idx in range(visible_count):
        rr = pygame.Rect(rect.x + S(10), row_top + idx * row_h, rect.w - S(20), row_h)
        if rr.collidepoint(mx, my):
            return "select", idx

    return None, None


def panel_wifi(screen, rect, fonts, data, now, *, neon_box, draw_scanline_shimmer, text_surf, draw_signal_list_rows, S, colors):
    PINK = colors["PINK"]
    CYAN = colors["CYAN"]
    BG = colors["BG"]
    MUTED = colors["MUTED"]

    networks = data.get("wifi_networks", [])
    scanning = data.get("wifi_scanning", False)

    neon_box(screen, rect, PINK, pulse=now + 0.2)
    draw_scanline_shimmer(screen, rect, now)

    selected_idx = data.get("wifi_selected_idx")
    if selected_idx is not None and not (0 <= selected_idx < len(networks)):
        selected_idx = None
        data["wifi_selected_idx"] = None

    title = f"WIFI ({len(networks)} found)"
    title_color = PINK
    screen.blit(text_surf(fonts["panel_title"], title, title_color), (rect.x + S(18), rect.y + S(12)))

    if scanning:
        scan_text = "SCANNING" if int(now * 4) % 2 == 0 else "..."
        scan_color = BG if int(now * 4) % 2 == 0 else PINK
        scan_surf = text_surf(fonts["sm"], scan_text, scan_color)
        screen.blit(scan_surf, (rect.right - S(18) - scan_surf.get_width(), rect.y + S(16)))

    if not networks:
        msg = "● SCANNING..." if scanning else "NO NETWORKS FOUND"
        screen.blit(text_surf(fonts["sm"], msg, MUTED), (rect.x + S(18), rect.y + S(56)))
        return

    if selected_idx is not None:
        ssid, dbm = networks[selected_idx]
        quality = _signal_quality(dbm)

        back_rect = pygame.Rect(rect.x + S(18), rect.y + S(12), S(120), S(34))
        pygame.draw.rect(screen, (24, 28, 54), back_rect, border_radius=S(5))
        pygame.draw.rect(screen, PINK, back_rect, 1, border_radius=S(5))
        screen.blit(text_surf(fonts["sm"], "< BACK", PINK), (back_rect.x + S(10), back_rect.y + S(6)))

        name_surf = text_surf(fonts["load_line"], str(ssid), TEXT)
        name_max_w = rect.w - S(40)
        if name_surf.get_width() > name_max_w:
            name_surf = name_surf.subsurface((0, 0, name_max_w, name_surf.get_height()))
        screen.blit(name_surf, (rect.x + S(18), rect.y + S(64)))

        stats_y = rect.y + S(118)
        screen.blit(text_surf(fonts["sm"], "SIGNAL", MUTED), (rect.x + S(18), stats_y))
        screen.blit(text_surf(fonts["panel_title"], f"{int(dbm)} dBm", PINK if dbm >= -70 else CYAN), (rect.x + S(18), stats_y + S(24)))

        screen.blit(text_surf(fonts["sm"], "QUALITY", MUTED), (rect.x + S(260), stats_y))
        screen.blit(text_surf(fonts["panel_title"], f"{quality}%", CYAN), (rect.x + S(260), stats_y + S(24)))

        deauth_rect = pygame.Rect(rect.right - S(210), rect.bottom - S(66), S(190), S(44))
        pygame.draw.rect(screen, (52, 10, 24), deauth_rect, border_radius=S(6))
        pygame.draw.rect(screen, PINK, deauth_rect, 2, border_radius=S(6))
        deauth_txt = text_surf(fonts["sm"], "DEAUTH", PINK)
        screen.blit(deauth_txt, (deauth_rect.centerx - deauth_txt.get_width() // 2, deauth_rect.centery - deauth_txt.get_height() // 2))

        deauth_msg = data.get("wifi_deauth_msg", "")
        deauth_at = float(data.get("wifi_deauth_at", 0.0))
        if deauth_msg and (now - deauth_at) <= 3.0:
            screen.blit(text_surf(fonts["sm"], deauth_msg, MUTED), (rect.x + S(18), rect.bottom - S(52)))
        return

    row_h = S(56)
    row_top = rect.y + S(48)
    max_rows = max(1, (rect.h - S(52)) // row_h)
    visible = networks[:max_rows]

    dbm_col_w = fonts["list_item"].size("-100dBm")[0] + S(8)
    bar_col_w = fonts["list_item"].size("█" * 5)[0] + S(6)
    name_max_w = rect.w - S(24) - bar_col_w - dbm_col_w

    for idx, entry in enumerate(visible):
        name, dbm = entry
        y = row_top + idx * row_h
        row_rect = pygame.Rect(rect.x + S(10), y, rect.w - S(20), row_h - S(2))
        pygame.draw.rect(screen, (12, 14, 30), row_rect, border_radius=S(4))
        if idx % 2 == 0:
            pygame.draw.rect(screen, (26, 30, 52), row_rect, 1, border_radius=S(4))

        bars = "".join("█" if i < max(0, min(5, int(round((_signal_quality(dbm) / 100) * 5)))) else "░" for i in range(5))
        bc = PINK if dbm >= -65 else CYAN if dbm >= -75 else MUTED
        bx = rect.x + S(16)
        screen.blit(text_surf(fonts["list_item"], bars, bc), (bx, y + S(4)))

        name_surf = fonts["list_item"].render(f" {name}", True, TEXT)
        if name_surf.get_width() > name_max_w:
            name_surf = name_surf.subsurface((0, 0, name_max_w, name_surf.get_height()))
        screen.blit(name_surf, (bx + bar_col_w, y + S(4)))

        dbm_str = f"{int(dbm)}dBm" if dbm is not None else ""
        screen.blit(text_surf(fonts["list_item"], dbm_str, MUTED), (rect.right - dbm_col_w, y + S(4)))
