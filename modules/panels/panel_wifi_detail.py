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

    ssid, dbm = selected_entry

    if deauth_screen:
        back_rect = pygame.Rect(rect.x + S(18), rect.bottom - S(66), S(140), S(44))
        pygame.draw.rect(screen, (24, 28, 54), back_rect, border_radius=S(5))
        pygame.draw.rect(screen, PINK, back_rect, 1, border_radius=S(5))
        back_txt = text_surf(fonts["sm"], "< BACK", PINK)
        screen.blit(back_txt, (back_rect.centerx - back_txt.get_width() // 2, back_rect.centery - back_txt.get_height() // 2))

        title = text_surf(fonts["panel_title"], "DEAUTH STATUS", PINK)
        screen.blit(title, (rect.x + S(18), rect.y + S(20)))

        target_label = text_surf(fonts["sm"], "TARGET", MUTED)
        screen.blit(target_label, (rect.x + S(18), rect.y + S(70)))
        target_surf = text_surf(fonts["load_line"], str(ssid), TEXT)
        target_max_w = rect.w - S(40)
        if target_surf.get_width() > target_max_w:
            target_surf = target_surf.subsurface((0, 0, target_max_w, target_surf.get_height()))
        screen.blit(target_surf, (rect.x + S(18), rect.y + S(98)))

        status_panel = pygame.Rect(rect.x + S(18), rect.y + S(160), rect.w - S(36), rect.h - S(252))
        pygame.draw.rect(screen, (12, 16, 34), status_panel, border_radius=S(6))
        pygame.draw.rect(screen, CYAN, status_panel, 1, border_radius=S(6))
        status_head = text_surf(fonts["sm"], "STATUS", CYAN)
        screen.blit(status_head, (status_panel.x + S(10), status_panel.y + S(8)))

        status_rect = pygame.Rect(
            status_panel.x + S(10),
            status_panel.y + S(34),
            status_panel.w - S(20),
            status_panel.h - S(44),
        )
        render_status(
            screen,
            status_rect,
            fonts,
            now,
            text_surf=text_surf,
            color=MUTED,
        )

        stop_rect = pygame.Rect(rect.right - S(210), rect.bottom - S(66), S(190), S(44))
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

    deauth_rect = pygame.Rect(rect.right - S(210), rect.bottom - S(66), S(190), S(44))
    pygame.draw.rect(screen, (52, 10, 24), deauth_rect, border_radius=S(6))
    pygame.draw.rect(screen, PINK, deauth_rect, 2, border_radius=S(6))
    deauth_txt = text_surf(fonts["sm"], "DEAUTH", PINK)
    screen.blit(deauth_txt, (deauth_rect.centerx - deauth_txt.get_width() // 2, deauth_rect.centery - deauth_txt.get_height() // 2))
