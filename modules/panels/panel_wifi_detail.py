import pygame

from modules.panels.panel_wifi_deauth import render_status


def _signal_quality(dbm):
    if dbm is None:
        return 0
    return max(0, min(100, int(round((dbm + 100) * (100.0 / 60.0)))))


def wifi_detail_click_action(mx, my, rect, selected_ssid, S, *, deauth_screen=False):
    back_rect = pygame.Rect(rect.x + S(18), rect.bottom - S(66), S(140), S(44))
    if deauth_screen:
        stop_rect = pygame.Rect(rect.right - S(210), rect.bottom - S(66), S(190), S(44))
        if back_rect.collidepoint(mx, my):
            return "back", None
        if stop_rect.collidepoint(mx, my):
            return "stop_deauth", None
        return None, None

    deauth_rect = pygame.Rect(rect.right - S(210), rect.bottom - S(66), S(190), S(44))
    if back_rect.collidepoint(mx, my):
        return "back", None
    if deauth_rect.collidepoint(mx, my):
        return "deauth", str(selected_ssid)
    return None, None


def render_wifi_detail(screen, rect, fonts, selected_entry, now, *, text_surf, S, deauth_screen=False, colors):
    PINK = colors["PINK"]
    CYAN = colors["CYAN"]
    MUTED = colors["MUTED"]
    TEXT = colors["TEXT"]

    ssid, dbm = selected_entry[0], selected_entry[1]
    security = selected_entry[2] if len(selected_entry) > 2 else ""

    if deauth_screen:
        btn_y = rect.bottom - S(66)
        back_rect = pygame.Rect(rect.x + S(18), btn_y, S(140), S(44))
        stop_rect = pygame.Rect(rect.right - S(210), btn_y, S(190), S(44))

        # Status panel fills full space above buttons
        panel_top = rect.y + S(8)
        panel_bottom = btn_y - S(8)
        status_panel = pygame.Rect(rect.x + S(8), panel_top, rect.w - S(16), panel_bottom - panel_top)
        pygame.draw.rect(screen, (12, 16, 34), status_panel, border_radius=S(6))
        pygame.draw.rect(screen, CYAN, status_panel, 1, border_radius=S(6))

        # SSID as panel label
        ssid_surf = text_surf(fonts["sm"], str(ssid), CYAN)
        ssid_max_w = status_panel.w - S(16)
        if ssid_surf.get_width() > ssid_max_w:
            ssid_surf = ssid_surf.subsurface((0, 0, ssid_max_w, ssid_surf.get_height()))
        screen.blit(ssid_surf, (status_panel.x + S(8), status_panel.y + S(6)))

        status_rect = pygame.Rect(
            status_panel.x + S(8),
            status_panel.y + ssid_surf.get_height() + S(10),
            status_panel.w - S(16),
            status_panel.h - ssid_surf.get_height() - S(16),
        )
        render_status(
            screen,
            status_rect,
            fonts,
            now,
            text_surf=text_surf,
            S=S,
            color=MUTED,
        )

        pygame.draw.rect(screen, (24, 28, 54), back_rect, border_radius=S(5))
        pygame.draw.rect(screen, PINK, back_rect, 1, border_radius=S(5))
        back_txt = text_surf(fonts["sm"], "< BACK", PINK)
        screen.blit(back_txt, (back_rect.centerx - back_txt.get_width() // 2, back_rect.centery - back_txt.get_height() // 2))

        pygame.draw.rect(screen, (14, 24, 44), stop_rect, border_radius=S(6))
        pygame.draw.rect(screen, CYAN, stop_rect, 2, border_radius=S(6))
        stop_txt = text_surf(fonts["sm"], "STOP", CYAN)
        screen.blit(stop_txt, (stop_rect.centerx - stop_txt.get_width() // 2, stop_rect.centery - stop_txt.get_height() // 2))
        return

    quality = _signal_quality(dbm)

    back_rect = pygame.Rect(rect.x + S(18), rect.bottom - S(66), S(140), S(44))
    pygame.draw.rect(screen, (24, 28, 54), back_rect, border_radius=S(5))
    pygame.draw.rect(screen, PINK, back_rect, 1, border_radius=S(5))
    back_txt = text_surf(fonts["sm"], "< BACK", PINK)
    screen.blit(back_txt, (back_rect.centerx - back_txt.get_width() // 2, back_rect.centery - back_txt.get_height() // 2))

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

    if security:
        sec_color = CYAN if security in ("WPA3", "WPA2/WPA3") else PINK if security == "WPA2" else MUTED
        screen.blit(text_surf(fonts["sm"], "SECURITY", MUTED), (rect.x + S(420), stats_y))
        screen.blit(text_surf(fonts["panel_title"], security, sec_color), (rect.x + S(420), stats_y + S(24)))

    deauth_rect = pygame.Rect(rect.right - S(210), rect.bottom - S(66), S(190), S(44))
    pygame.draw.rect(screen, (52, 10, 24), deauth_rect, border_radius=S(6))
    pygame.draw.rect(screen, PINK, deauth_rect, 2, border_radius=S(6))
    deauth_txt = text_surf(fonts["sm"], "DEAUTH", PINK)
    screen.blit(deauth_txt, (deauth_rect.centerx - deauth_txt.get_width() // 2, deauth_rect.centery - deauth_txt.get_height() // 2))
