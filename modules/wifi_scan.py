import shutil
import subprocess
import time


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


def _wifi_interface():
    """Return the first wireless interface name found via iw, or 'wlan0'."""
    lines = run_command_lines(["iw", "dev"])
    for line in lines:
        if line.strip().startswith("Interface"):
            return line.strip().split()[-1]
    return "wlan0"


def read_wifi_networks():
    """Return list of (ssid, signal_dbm) tuples, best signal per unique SSID."""
    iface = _wifi_interface()
    lines = run_command_lines(["iw", "dev", iface, "scan", "dump"], timeout=5)
    if not lines:
        print(f"[scan] wifi: iw scan dump returned no output (iface={iface})")
        return []

    best = {}
    current_signal = None
    for ln in lines:
        if "signal:" in ln:
            try:
                current_signal = float(ln.split("signal:")[-1].split()[0])
            except ValueError:
                pass
        elif "SSID:" in ln:
            ssid = ln.split("SSID:", 1)[-1].strip()
            if ssid and current_signal is not None:
                if ssid not in best or current_signal > best[ssid]:
                    best[ssid] = current_signal
            current_signal = None
    return sorted(best.items(), key=lambda x: -x[1])


def bg_scan_wifi(data, cache):
    if shutil.which("iw") is None:
        if not cache.get("wifi_unavailable", False):
            print("[scan] wifi: iw not found")
        data["wifi_networks"] = []
        data["wifi"] = 0
        cache["wifi_unavailable"] = True
        cache["wifi_scanning"] = False
        return

    t0 = time.time()
    result = read_wifi_networks()
    print(f"[scan] wifi: {len(result)} ({time.time() - t0:.1f}s)")
    data["wifi_networks"] = result
    data["wifi"] = len(result)
    cache["wifi_scanning"] = False

