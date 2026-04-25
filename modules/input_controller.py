import time

import pygame

from modules.draw import S
from modules.sound_manager import play_click


def _apply_menu_selection(mx, my, selected, current_view, light_on):
    menu_x0 = S(14)
    menu_x1 = S(14) + S(170)
    if not (menu_x0 <= mx <= menu_x1):
        return selected, current_view, light_on

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

    return selected, current_view, light_on


def handle_input(selected, current_view, light_on, click_sound, ripples):
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
            selected, current_view, light_on = _apply_menu_selection(mx, my, selected, current_view, light_on)

    return running, selected, current_view, light_on
