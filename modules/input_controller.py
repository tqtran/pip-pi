import time

import pygame

from modules.draw import S
from modules.panels.panel_wifi import wifi_click_action
from modules.sound_manager import play_click


def _apply_menu_selection(mx, my, selected, current_view, light_on):
    menu_x0 = S(14)
    menu_x1 = S(14) + S(170)
    if not (menu_x0 <= mx <= menu_x1):
        return selected, current_view, light_on, False

    tile_h = S(78)
    tile_gap = S(8)
    start_y = S(54)
    for i in range(5):
        y = start_y + i * (tile_h + tile_gap)
        if y <= my <= y + tile_h:
            if i == 4:
                light_on = not light_on
            else:
                light_on = False
                selected = i
                if i == 2:
                    current_view = "home"
                elif i == 0:
                    current_view = "wifi"
                elif i == 1:
                    current_view = "bluetooth"
                elif i == 3:
                    current_view = "config"
            break

    return selected, current_view, light_on, True


def _content_rect():
    surf = pygame.display.get_surface()
    if surf is None:
        return None
    width, height = surf.get_size()
    rx = S(14) + S(170) + S(10)
    rw = width - rx - S(14)
    return pygame.Rect(rx, S(54), rw, height - S(68))


def handle_input(selected, current_view, light_on, click_sound, ripples, data=None):
    running = True

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
            ripples.append({"x": mx, "y": my, "born": time.time()})
            play_click(click_sound)
            selected, current_view, light_on, menu_handled = _apply_menu_selection(mx, my, selected, current_view, light_on)

            if not menu_handled and data is not None and current_view == "wifi":
                rect = _content_rect()
                if rect is not None and rect.collidepoint(mx, my):
                    action, payload = wifi_click_action(mx, my, rect, data, S)
                    if action == "select":
                        data["wifi_selected_idx"] = payload
                    elif action == "back":
                        data["wifi_selected_idx"] = None
                    elif action == "deauth":
                        idx = int(payload)
                        nets = data.get("wifi_networks", [])
                        if 0 <= idx < len(nets):
                            ssid = str(nets[idx][0])
                            data["wifi_deauth_msg"] = f"DEAUTH sent to {ssid}"
                            data["wifi_deauth_at"] = time.time()

    return running, selected, current_view, light_on
