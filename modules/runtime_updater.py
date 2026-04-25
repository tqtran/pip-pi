import threading
import time

from modules.app_config import DEFAULT_CONFIG
from modules.ble_scan import bg_scan_ble
from modules.thread_control import get_shutdown_event, is_shutting_down, start_managed_thread
from modules.system_metrics import read_cpu_percent, read_mem_percent, read_storage_percent, read_temp_c, read_uptime_str
from modules.wifi_scan import bg_scan_wifi


def update_data(data, cache, start_time, now, config):
    if is_shutting_down():
        cache["wifi_scanning"] = False
        cache["ble_scanning"] = False
        data["wifi_scanning"] = False
        data["ble_scanning"] = False
        return

    intervals = config.get("refresh_intervals", {})
    scan_intervals = config.get("scan_intervals", {})
    scan_behavior = config.get("scan_behavior", {})

    load_seconds = float(intervals.get("load_seconds", DEFAULT_CONFIG["refresh_intervals"]["load_seconds"]))
    stats_seconds = float(intervals.get("stats_seconds", DEFAULT_CONFIG["refresh_intervals"]["stats_seconds"]))
    ble_seconds = float(scan_intervals.get("ble_seconds", DEFAULT_CONFIG["scan_intervals"]["ble_seconds"]))
    ble_first_window = float(scan_behavior.get("ble_first_window_seconds", DEFAULT_CONFIG["scan_behavior"]["ble_first_window_seconds"]))
    ble_next_window = float(scan_behavior.get("ble_window_seconds", DEFAULT_CONFIG["scan_behavior"]["ble_window_seconds"]))

    # --- scan policy based on current view ---
    current_view = data.get("current_view", "home")
    deauth_active = bool(data.get("wifi_deauth_screen", False))
    wifi_focused = current_view in ("wifi",) or bool(data.get("wifi_selected_ssid"))

    if deauth_active:
        # Deauth mode: suppress all background scanning
        allow_wifi_scan = False
        allow_ble_scan = False
        wifi_seconds = float(scan_intervals.get("wifi_seconds", DEFAULT_CONFIG["scan_intervals"]["wifi_seconds"]))
    elif wifi_focused:
        # Wi-Fi panel / detail: fast wifi refresh, no BLE
        wifi_seconds = 5.0
        allow_wifi_scan = True
        allow_ble_scan = False
    else:
        wifi_seconds = float(scan_intervals.get("wifi_seconds", DEFAULT_CONFIG["scan_intervals"]["wifi_seconds"]))
        allow_wifi_scan = True
        allow_ble_scan = True

    if now - cache.get("load_refresh_at", -load_seconds) >= load_seconds:
        cpu = read_cpu_percent(cache)
        mem = read_mem_percent()
        if cpu is not None:
            data["cpu"] = cpu
        if mem is not None:
            data["mem"] = mem
        cache["load_refresh_at"] = now

    if now - cache.get("stats_refresh_at", -stats_seconds) >= stats_seconds:
        store = read_storage_percent()
        temp_c = read_temp_c()
        if store is not None:
            data["store"] = store
        if temp_c is not None:
            data["temp"] = max(-40.0, min(140.0, temp_c))
        cache["stats_refresh_at"] = now

    if (allow_wifi_scan
            and not cache.get("wifi_unavailable", False)
            and now - cache.get("wifi_refresh_at", -wifi_seconds) >= wifi_seconds):
        if not cache.get("wifi_scanning", False):
            cache["wifi_scanning"] = True
            cache["wifi_scan_started"] = now
            cache["wifi_refresh_at"] = now
            worker = start_managed_thread(
                "wifi-scan",
                bg_scan_wifi,
                args=(data, cache, get_shutdown_event()),
                daemon=True,
            )
            if worker is None:
                cache["wifi_scanning"] = False

    if (allow_ble_scan
            and now - cache.get("ble_refresh_at", -ble_seconds) >= ble_seconds):
        if not cache.get("ble_scanning", False):
            ble_scan_count = int(cache.get("ble_scan_count", 0))
            ble_window = ble_first_window if ble_scan_count == 0 else ble_next_window
            cache["ble_scanning"] = True
            cache["ble_scan_started"] = now
            cache["ble_refresh_at"] = now
            cache["ble_scan_count"] = ble_scan_count + 1
            worker = start_managed_thread(
                "ble-scan",
                bg_scan_ble,
                args=(data, cache, ble_window, get_shutdown_event()),
                daemon=True,
            )
            if worker is None:
                cache["ble_scanning"] = False

    data["wifi_scanning"] = cache.get("wifi_scanning", False)
    data["ble_scanning"] = cache.get("ble_scanning", False)
    data["wifi_refresh_at"] = cache.get("wifi_refresh_at", now)
    data["ble_refresh_at"] = cache.get("ble_refresh_at", now)

    uptime = read_uptime_str()

    data["clock"] = time.strftime("%H:%M")
    data["last_update"] = time.strftime("%H:%M:%S")
    if uptime is not None:
        data["uptime"] = uptime
    else:
        elapsed = int(time.time() - start_time)
        hh = elapsed // 3600
        mm = (elapsed % 3600) // 60
        data["uptime"] = f"{hh:01d}:{mm:02d}"
