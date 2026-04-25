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


def _parse_security(block_lines):
    """Derive security string from a single BSS block (lines already stripped)."""
    has_rsn = False
    has_wpa = False
    has_privacy = False
    akm = set()
    in_rsn = False

    for ln in block_lines:
        low = ln.lower()
        if low.startswith("capability:"):
            has_privacy = "privacy" in low
        elif low == "rsn:":
            has_rsn = True
            in_rsn = True
        elif low.startswith("wpa:"):
            has_wpa = True
            in_rsn = False
        elif low.endswith(":") and not low.startswith("*"):
            in_rsn = False  # entering a different subsection

        if in_rsn and ("authentication suites:" in low or "akm suites:" in low):
            rest = ln.split(":", 1)[-1].strip().upper()
            for token in rest.split():
                akm.add(token)

    if has_rsn:
        has_sae = "SAE" in akm
        has_psk = "PSK" in akm
        if has_sae and has_psk:
            return "WPA2/WPA3"
        if has_sae:
            return "WPA3"
        return "WPA2"
    if has_wpa:
        return "WPA"
    if has_privacy:
        return "WEP"
    return "Open"


def read_wifi_networks():
    """Return list of (ssid, signal_dbm, security) tuples, best signal per unique SSID."""
    iface = _wifi_interface()
    lines = run_command_lines(["iw", "dev", iface, "scan", "dump"], timeout=5)
    if not lines:
        print(f"[scan] wifi: iw scan dump returned no output (iface={iface})")
        return []

    # Split output into per-BSS blocks
    blocks = []
    current = []
    for ln in lines:
        if ln.startswith("BSS "):
            if current:
                blocks.append(current)
            current = [ln]
        else:
            current.append(ln)
    if current:
        blocks.append(current)

    best = {}  # ssid -> (signal, security)
    for block in blocks:
        ssid = None
        signal = None
        for ln in block:
            if ln.startswith("SSID:"):
                ssid = ln.split("SSID:", 1)[-1].strip()
            elif ln.startswith("signal:"):
                try:
                    signal = float(ln.split("signal:", 1)[-1].split()[0])
                except ValueError:
                    pass
        if not ssid or signal is None:
            continue
        security = _parse_security(block)
        if ssid not in best or signal > best[ssid][0]:
            best[ssid] = (signal, security)

    return sorted(
        [(ssid, sig, sec) for ssid, (sig, sec) in best.items()],
        key=lambda x: -x[1],
    )


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

