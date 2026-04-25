import pygame

from modules.panels.panel_wifi_detail import render_wifi_detail, wifi_detail_click_action


def _signal_quality(dbm):
    if dbm is None:
        return 0
    return max(0, min(100, int(round((dbm + 100) * (100.0 / 60.0)))))


def wifi_click_action(mx, my, rect, data, S):
    networks = data.get("wifi_networks", [])
    selected_ssid = data.get("wifi_selected_ssid")
    selected_present = selected_ssid is not None and any(str(n[0]) == str(selected_ssid) for n in networks)

    if selected_present:
        deauth_screen = bool(data.get("wifi_deauth_screen", False))
        return wifi_detail_click_action(mx, my, rect, selected_ssid, S, deauth_screen=deauth_screen)

    row_h = S(56)
    row_top = rect.y + S(48)
    max_rows = max(1, (rect.h - S(52)) // row_h)
    visible_count = min(len(networks), max_rows)

    for idx in range(visible_count):
        rr = pygame.Rect(rect.x + S(10), row_top + idx * row_h, rect.w - S(20), row_h)
        if rr.collidepoint(mx, my):
            return "select", str(networks[idx][0])

    return None, None


def panel_wifi(screen, rect, fonts, data, now, *, neon_box, draw_scanline_shimmer, text_surf, draw_signal_list_rows, S, colors):
    PINK = colors["PINK"]
    CYAN = colors["CYAN"]
    BG = colors["BG"]
    MUTED = colors["MUTED"]
    TEXT = colors["TEXT"]

    networks = data.get("wifi_networks", [])
    scanning = data.get("wifi_scanning", False)

    neon_box(screen, rect, PINK, pulse=now + 0.2)
    draw_scanline_shimmer(screen, rect, now)

    selected_ssid = data.get("wifi_selected_ssid")
    selected_entry = None
    if selected_ssid is not None:
        for entry in networks:
            if str(entry[0]) == str(selected_ssid):
                selected_entry = entry
                break
        if selected_entry is None:
            data["wifi_selected_ssid"] = None

    if selected_entry is None:
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

    if selected_entry is not None:
        deauth_screen = bool(data.get("wifi_deauth_screen", False))
        render_wifi_detail(
            screen,
            rect,
            fonts,
            selected_entry,
            now,
            text_surf=text_surf,
            S=S,
            deauth_screen=deauth_screen,
            colors={"PINK": PINK, "CYAN": CYAN, "MUTED": MUTED, "TEXT": TEXT},
        )
        return

    row_h = S(56)
    row_top = rect.y + S(48)
    max_rows = max(1, (rect.h - S(52)) // row_h)
    visible = networks[:max_rows]

    dbm_col_w = fonts["list_item"].size("-100dBm")[0] + S(8)
    bar_w = max(2, S(9))
    bar_h = max(2, S(14))
    bar_gap = max(1, S(2))
    bar_col_w = (bar_w * 5) + (bar_gap * 4) + S(6)
    name_max_w = rect.w - S(24) - bar_col_w - dbm_col_w

    for idx, entry in enumerate(visible):
        name, dbm = entry
        y = row_top + idx * row_h
        row_rect = pygame.Rect(rect.x + S(10), y, rect.w - S(20), row_h - S(2))
        pygame.draw.rect(screen, (12, 14, 30), row_rect, border_radius=S(4))
        if idx % 2 == 0:
            pygame.draw.rect(screen, (26, 30, 52), row_rect, 1, border_radius=S(4))

        bars_on = max(0, min(5, int(round((_signal_quality(dbm) / 100) * 5))))
        bc = PINK if dbm >= -65 else CYAN if dbm >= -75 else MUTED
        bx = rect.x + S(16)
        by = y + S(12)
        for bi in range(5):
            bar_color = bc if bi < bars_on else (28, 34, 62)
            pygame.draw.rect(screen, bar_color, (bx + bi * (bar_w + bar_gap), by, bar_w, bar_h), border_radius=2)

        name_surf = fonts["list_item"].render(f" {name}", True, TEXT)
        if name_surf.get_width() > name_max_w:
            name_surf = name_surf.subsurface((0, 0, name_max_w, name_surf.get_height()))
        screen.blit(name_surf, (bx + bar_col_w, y + S(4)))

        dbm_str = f"{int(dbm)}dBm" if dbm is not None else ""
        screen.blit(text_surf(fonts["list_item"], dbm_str, MUTED), (rect.right - dbm_col_w, y + S(4)))
