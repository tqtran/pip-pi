import shutil
import subprocess
import time


def run_command_lines(cmd, timeout=2, stop_event=None):
    proc = None
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.time() + max(0.1, float(timeout))

        while proc.poll() is None:
            if stop_event is not None and stop_event.is_set():
                proc.terminate()
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return []
            if time.time() >= deadline:
                proc.kill()
                print(f"[cmd] {cmd[0]} timed out after {timeout}s")
                return []
            time.sleep(0.05)

        stdout, stderr = proc.communicate(timeout=0.2)
        if proc.returncode != 0 and stderr:
            print(f"[cmd] {cmd[0]} stderr: {stderr.strip()[:120]}")
        return [line.strip() for line in stdout.splitlines() if line.strip()]
    except subprocess.TimeoutExpired:
        print(f"[cmd] {cmd[0]} timed out after {timeout}s")
        return []
    except Exception as exc:
        print(f"[cmd] {cmd[0]} failed: {exc}")
        return []
    finally:
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass


def _wifi_interface():
    """Return the first wireless interface name found via iw, or 'wlan0'."""
    lines = run_command_lines(["iw", "dev"])
    for line in lines:
        if line.strip().startswith("Interface"):
            return line.strip().split()[-1]
    return "wlan0"

def _parse_security(block_lines):
    """Derive security string from a single BSS block."""
    has_rsn = False
    has_wpa = False
    has_privacy = False
    akm_text = ""
    in_rsn = False

    for ln in block_lines:
        low = ln.lower().strip()

        if low.startswith("capability:"):
            has_privacy = "privacy" in low

        elif low.startswith("rsn:"):
            has_rsn = True
            in_rsn = True

        elif low.startswith("wpa:"):
            has_wpa = True
            in_rsn = False

        elif low.endswith(":") and not low.startswith("*"):
            in_rsn = False

        if in_rsn and ("authentication suites:" in low or "akm suites:" in low):
            akm_text += " " + ln.split(":", 1)[-1].strip().upper()

    if has_rsn:
        has_sae = "SAE" in akm_text
        has_psk = "PSK" in akm_text
        has_8021x = "802.1X" in akm_text or "IEEE" in akm_text

        if has_sae and has_psk:
            return "WPA2/WPA3"
        if has_sae:
            return "WPA3"
        if has_8021x:
            return "WPA2-ENT"
        return "WPA2"

    if has_wpa:
        return "WPA"
    if has_privacy:
        return "WEP"
    return "Open"


def read_wifi_networks(stop_event=None):
    """Return list of (ssid, signal_dbm, security) tuples, best signal per unique SSID."""
    iface = _wifi_interface()
    lines = run_command_lines(["iw", "dev", iface, "scan", "dump"], timeout=5, stop_event=stop_event)
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


def bg_scan_wifi(data, cache, stop_event=None):
    if stop_event is not None and stop_event.is_set():
        cache["wifi_scanning"] = False
        return

    if shutil.which("iw") is None:
        if not cache.get("wifi_unavailable", False):
            print("[scan] wifi: iw not found")
        data["wifi_networks"] = []
        data["wifi"] = 0
        cache["wifi_unavailable"] = True
        cache["wifi_scanning"] = False
        return

    t0 = time.time()
    result = read_wifi_networks(stop_event=stop_event)
    if stop_event is not None and stop_event.is_set():
        cache["wifi_scanning"] = False
        return
    print(f"[scan] wifi: {len(result)} ({time.time() - t0:.1f}s)")
    data["wifi_networks"] = result
    data["wifi"] = len(result)
    cache["wifi_scanning"] = False

