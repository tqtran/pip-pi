import os
import subprocess
import sys
import time

import pygame

from modules.app_config import CONFIG, write_config_file
from modules.draw import S
from modules.panels.panel_config import config_click_action
from modules.panels.panel_wifi_deauth import begin_deauth, stop_deauth
from modules.panels.panel_wifi import wifi_click_action
from modules.sound_manager import play_click
from modules.thread_control import request_shutdown, start_managed_thread


def _summarize_git_pull(returncode, output):
    text = (output or "").strip()
    low = text.lower()

    if "already up to date" in low or "already up-to-date" in low:
        return "Update: already up to date"

    if returncode == 0:
        if "fast-forward" in low or "updating " in low or "files changed" in low:
            return "Update complete: pulled latest changes"
        return "Update complete"

    if "conflict" in low or "merge conflict" in low:
        return "Update failed: merge conflict"
    if "could not resolve host" in low:
        return "Update failed: network/host error"
    if "not a git repository" in low:
        return "Update failed: not a git repo"
    if "permission denied" in low:
        return "Update failed: permission denied"
    if "authentication failed" in low:
        return "Update failed: authentication"

    first = text.splitlines()[0].strip() if text else "unknown error"
    return f"Update failed: {first[:60]}"


def _run_git_pull_async(data):
    if data is None:
        return

    if data.get("update_running", False):
        data["status_msg"] = "Update already running..."
        data["status_msg_at"] = time.time()
        return

    data["update_running"] = True
    data["status_msg"] = "Running git pull..."
    data["status_msg_at"] = time.time()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_cmd = ["git", "-C", repo_root, "pull"]
    cmd_candidates = [git_cmd] if os.name == "nt" else [["sudo"] + git_cmd, git_cmd]

    def _worker():
        try:
            output = ""
            rc = 1

            for cmd in cmd_candidates:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
                    rc = int(result.returncode)
                    break
                except FileNotFoundError:
                    continue

            data["status_msg"] = _summarize_git_pull(rc, output)
            data["status_msg_at"] = time.time()
        except Exception as exc:
            data["status_msg"] = f"Update failed: {str(exc)[:60]}"
            data["status_msg_at"] = time.time()
        finally:
            data["update_running"] = False

    worker = start_managed_thread("git-pull-update", _worker, daemon=True)
    if worker is None:
        data["update_running"] = False
        data["status_msg"] = "Update skipped: app is shutting down"
        data["status_msg_at"] = time.time()


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
            request_shutdown()
            stop_deauth()
            if data is not None:
                data["wifi_deauth_screen"] = False
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                request_shutdown()
                stop_deauth()
                if data is not None:
                    data["wifi_deauth_screen"] = False
                running = False
            elif event.key == pygame.K_DOWN:
                selected = (selected + 1) % 5
            elif event.key == pygame.K_UP:
                selected = (selected - 1) % 5
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            ripples.append({"x": mx, "y": my, "born": time.time()})
            play_click(click_sound)
            old_view = current_view
            was_deauth_screen = bool(data.get("wifi_deauth_screen", False)) if data is not None else False
            selected, current_view, light_on, menu_handled = _apply_menu_selection(mx, my, selected, current_view, light_on)

            # If navigation leaves wifi while deauth screen is open, stop the worker.
            if menu_handled and data is not None and old_view == "wifi" and current_view != "wifi" and was_deauth_screen:
                stop_deauth()
                data["wifi_deauth_screen"] = False

            # Reset config draft whenever the user freshly enters config
            if current_view == "config" and old_view != "config" and data is not None:
                data["config_draft"] = None

            if not menu_handled and data is not None and current_view == "config":
                rect = _content_rect()
                if rect is not None and rect.collidepoint(mx, my):
                    action, _ = config_click_action(mx, my, rect, data, CONFIG, S)
                    if action == "save":
                        draft = data.get("config_draft")
                        if draft:
                            for section, vals in draft.items():
                                if section in CONFIG and isinstance(vals, dict):
                                    CONFIG[section].update(vals)
                            write_config_file(CONFIG)
                        data["config_draft"] = None
                        current_view = "home"
                        selected = 2
                    elif action == "cancel":
                        data["config_draft"] = None
                        current_view = "home"
                        selected = 2
                    elif action == "toggle_fullscreen":
                        pygame.display.toggle_fullscreen()
                        is_fs = bool(pygame.display.get_surface().get_flags() & pygame.FULLSCREEN)
                        if data is not None:
                            data["status_msg"] = "Fullscreen ON" if is_fs else "Fullscreen OFF"
                            data["status_msg_at"] = time.time()
                    elif action == "update":
                        _run_git_pull_async(data)
                    elif action == "restart":
                        if data is not None:
                            data["status_msg"] = "Restarting..."
                        pygame.display.flip()
                        pygame.time.wait(600)
                        pygame.quit()
                        os.execv(sys.executable, [sys.executable] + sys.argv)

            if not menu_handled and data is not None and current_view == "wifi":
                rect = _content_rect()
                if rect is not None and rect.collidepoint(mx, my):
                    action, payload = wifi_click_action(mx, my, rect, data, S)
                    if action == "select":
                        data["wifi_selected_ssid"] = str(payload)
                        data["wifi_deauth_screen"] = False
                    elif action == "back":
                        if data.get("wifi_deauth_screen", False):
                            stop_deauth()
                            data["wifi_deauth_screen"] = False
                        else:
                            data["wifi_selected_ssid"] = None
                            data["wifi_deauth_screen"] = False
                    elif action == "deauth":
                        ssid = str(payload)
                        started = begin_deauth("sim-ap", ssid, "wlan0")
                        data["wifi_deauth_screen"] = True
                        data["wifi_deauth_msg"] = f"DEAUTH sim started for {ssid}" if started else "DEAUTH simulation already running"
                        data["wifi_deauth_at"] = time.time()
                    elif action == "stop_deauth":
                        stopped = stop_deauth()
                        data["wifi_deauth_msg"] = "DEAUTH simulation stopped" if stopped else "DEAUTH simulation already stopped"
                        data["wifi_deauth_at"] = time.time()

    return running, selected, current_view, light_on
