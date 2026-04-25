import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time

from modules.thread_control import start_managed_thread

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
BLE_NAME_CACHE_PATH = os.path.join(DATA_DIR, "ble-name-cache.json")
LEGACY_BLE_NAME_CACHE_PATH = os.path.join(PROJECT_ROOT, "ble-name-cache.json")


def maybe_migrate_legacy_ble_cache():
    if os.path.exists(BLE_NAME_CACHE_PATH) or not os.path.exists(LEGACY_BLE_NAME_CACHE_PATH):
        return
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.replace(LEGACY_BLE_NAME_CACHE_PATH, BLE_NAME_CACHE_PATH)
        print(f"[ble-cache] moved legacy cache to {BLE_NAME_CACHE_PATH}")
    except Exception as exc:
        print(f"[ble-cache] failed to migrate legacy cache: {exc}")


def load_ble_name_cache():
    maybe_migrate_legacy_ble_cache()
    try:
        if os.path.exists(BLE_NAME_CACHE_PATH):
            with open(BLE_NAME_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}
    except Exception as exc:
        print(f"[ble-cache] failed to load {BLE_NAME_CACHE_PATH}: {exc}")
    return {}


def save_ble_name_cache(cache_map):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(BLE_NAME_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_map, f, indent=2, sort_keys=True)
    except Exception as exc:
        print(f"[ble-cache] failed to save {BLE_NAME_CACHE_PATH}: {exc}")


def valid_ble_name(name, mac):
    if not name:
        return False
    n = name.strip()
    if not n:
        return False
    if n.lower() in {"unknown", "(unknown)", "n/a", "none"}:
        return False
    if n.upper() == mac.upper():
        return False
    return True


def run_command_lines(cmd, timeout=2):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0 and result.stderr:
            print(f"[cmd] {cmd[0]} stderr: {result.stderr.strip()[:120]}")
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.TimeoutExpired:
        print(f"[cmd] {cmd[0]} timed out after {timeout}s")
        return []
    except Exception as exc:
        print(f"[cmd] {cmd[0]} failed: {exc}")
        return []


BLE_NAME_CACHE = load_ble_name_cache()
BLE_NAME_CACHE_LOCK = threading.Lock()


def read_ble_devices():
    """Read discovered devices and return list of (name, mac) tuples sorted by name."""
    lines = run_command_lines(["bluetoothctl", "devices"])
    if not lines:
        print("[scan] ble: bluetoothctl returned no output")
        return []

    devices = []
    seen_macs = set()
    for ln in lines:
        parts = ln.strip().split(None, 2)
        if len(parts) >= 2 and parts[0] == "Device":
            mac = parts[1]
            if mac in seen_macs:
                continue
            seen_macs.add(mac)
            name = parts[2] if len(parts) == 3 else ""
            if not valid_ble_name(name, mac):
                with BLE_NAME_CACHE_LOCK:
                    cached_name = BLE_NAME_CACHE.get(mac)
                name = cached_name if valid_ble_name(cached_name, mac) else mac
            devices.append((name, mac))
    return sorted(devices, key=lambda x: x[0].lower())


def bg_scan_ble(data, cache, scan_window_seconds, stop_event=None):
    t0 = time.time()
    if stop_event is not None and stop_event.is_set():
        cache["ble_scanning"] = False
        return

    if shutil.which("bluetoothctl") is None:
        print("[scan] ble: bluetoothctl not found")
        cache["ble_scanning"] = False
        return

    names = {}
    rssis = {}
    proc = None
    feeder_stop = threading.Event()
    feeder_thread = None
    try:
        proc = subprocess.Popen(
            ["bluetoothctl", "scan", "on"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

        line_q = queue.Queue()

        def _feeder(stream, q):
            try:
                for ln in stream:
                    if feeder_stop.is_set():
                        break
                    q.put(ln)
            except Exception:
                pass

        feeder_thread = start_managed_thread("ble-feeder", _feeder, args=(proc.stdout, line_q), daemon=True)

        deadline = time.time() + max(1.0, float(scan_window_seconds))
        while time.time() < deadline and (stop_event is None or not stop_event.is_set()):
            try:
                line = line_q.get(timeout=0.25)
            except queue.Empty:
                continue

            clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", line).strip()
            if not clean or clean.startswith("[bluetooth]"):
                continue

            parts = clean.split(None, 4)
            if len(parts) >= 3 and parts[1] == "Device":
                mac = parts[2]
                if len(parts) >= 4:
                    rest = " ".join(parts[3:]).strip()
                    if rest.startswith("RSSI:"):
                        try:
                            rssi = int(rest.split(":", 1)[1].strip())
                            if mac not in rssis or rssi > rssis[mac]:
                                rssis[mac] = rssi
                        except ValueError:
                            pass
                    elif rest.startswith("Name:") or rest.startswith("Alias:"):
                        candidate = rest.split(":", 1)[1].strip()
                        if candidate:
                            names[mac] = candidate
                    elif ":" not in rest:
                        names[mac] = rest
    finally:
        feeder_stop.set()
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

        if feeder_thread is not None and feeder_thread.is_alive():
            feeder_thread.join(timeout=1.0)

        subprocess.run(["bluetoothctl", "scan", "off"], timeout=3, capture_output=True)

        if stop_event is not None and stop_event.is_set():
            cache["ble_scanning"] = False
            return

        static = read_ble_devices()
        seen = set(names.keys()) | set(rssis.keys())
        for (name, mac) in static:
            if mac not in seen:
                names[mac] = name

        result = []
        cache_changed = False
        for mac in set(names.keys()) | set(rssis.keys()):
            name = names.get(mac, "").strip()

            if valid_ble_name(name, mac):
                with BLE_NAME_CACHE_LOCK:
                    if BLE_NAME_CACHE.get(mac) != name:
                        BLE_NAME_CACHE[mac] = name
                        cache_changed = True

            if not valid_ble_name(name, mac):
                with BLE_NAME_CACHE_LOCK:
                    cached_name = BLE_NAME_CACHE.get(mac)
                if valid_ble_name(cached_name, mac):
                    name = cached_name
                else:
                    name = mac

            rssi = rssis.get(mac)
            result.append((name, mac, rssi))

        result.sort(key=lambda x: (x[2] is None, -(x[2] or 0)))
        print(f"[scan] ble: {len(result)} ({time.time() - t0:.1f}s)")
        data["ble_devices"] = result
        data["ble"] = len(result)
        cache["ble_scanning"] = False

        if cache_changed:
            with BLE_NAME_CACHE_LOCK:
                save_ble_name_cache(BLE_NAME_CACHE)
