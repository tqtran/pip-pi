#!/usr/bin/env python3
"""
pip-pi dashboard prototype.

Reference-inspired neon layout using rectangles, lines, and text only.
No image assets required.
"""

import sys
import time

import pygame
from modules.app_config import CONFIG, DEFAULT_CONFIG
from modules.draw import BASE_H, BASE_W, RIPPLE_LIFE, TEXT, configure_layout, draw_frame, make_fonts
from modules.input_controller import handle_input
from modules.runtime_updater import update_data
from modules.sound_manager import init_click_sound

FPS = 30


def init_pygame_or_die():
    """Initialize pygame and verify font support with a concrete render test."""
    print(f"[startup] python: {sys.executable}")
    print(f"[startup] pygame: {getattr(pygame, '__file__', 'unknown')}")

    pygame.init()
    try:
        if not hasattr(pygame, "font"):
            raise RuntimeError("pygame.font module is missing")

        pygame.font.init()
        test_font = pygame.font.SysFont("dejavusansmono", 16, bold=True)
        test_font.render("font-ok", True, TEXT)
        print("[startup] pygame.font: ok")
    except Exception as exc:
        print(f"[startup] pygame.font failed: {exc}")
        print("[startup] likely causes: broken pygame install, missing SDL_ttf, or local module shadowing")
        pygame.quit()
        raise SystemExit(1)


def main():
    init_pygame_or_die()

    info = pygame.display.Info()
    width = info.current_w
    height = info.current_h
    scale = min(width / BASE_W, height / BASE_H)
    configure_layout(width, height, scale)
    print(f"[startup] display: {width}x{height}  scale: {scale:.3f}")

    pygame.display.set_caption("pip-pi live intel")
    pygame.mouse.set_visible(False)

    flags = pygame.FULLSCREEN if "--fullscreen" in set(sys.argv[1:]) else 0
    screen = pygame.display.set_mode((width, height), flags)
    clock = pygame.time.Clock()

    fonts = make_fonts()
    click_sound = init_click_sound()
    selected = 2
    current_view = "home"
    light_on = False
    start = time.time()
    data = {
        "wifi": 0,
        "ble": 0,
        "cpu": 0,
        "mem": 0,
        "store": 0,
        "temp": 0,
        "clock": "00:00",
        "last_update": "--:--:--",
        "uptime": "0:00:00",
        "wifi_scanning": False,
        "ble_scanning": False,
        "wifi_networks": [],
        "ble_devices": [],
        "wifi_selected_ssid": None,
        "wifi_deauth_msg": "",
        "wifi_deauth_at": 0.0,
    }

    _scan_intervals = CONFIG.get("scan_intervals", {})
    _scan_behavior = CONFIG.get("scan_behavior", {})
    _wifi_secs = float(_scan_intervals.get("wifi_seconds", DEFAULT_CONFIG["scan_intervals"]["wifi_seconds"]))
    _ble_secs = float(_scan_intervals.get("ble_seconds", DEFAULT_CONFIG["scan_intervals"]["ble_seconds"]))
    _ble_stagger = float(_scan_behavior.get("ble_stagger_seconds", DEFAULT_CONFIG["scan_behavior"]["ble_stagger_seconds"]))
    _now = time.time()
    cache = {
        "wifi_refresh_at": _now - _wifi_secs,
        "ble_refresh_at": _now - _ble_secs + _ble_stagger,
    }
    ripples = []

    running = True
    while running:
        running, selected, current_view, light_on = handle_input(
            selected=selected,
            current_view=current_view,
            light_on=light_on,
            click_sound=click_sound,
            ripples=ripples,
            data=data,
        )

        now = time.time()
        update_data(data, cache, start, now, CONFIG)
        draw_frame(screen, fonts, data, selected, current_view, light_on, now, CONFIG, ripples)

        ripples = [rp for rp in ripples if (now - rp["born"]) < RIPPLE_LIFE]
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
