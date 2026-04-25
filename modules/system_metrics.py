#!/usr/bin/env python3
"""Linux/Raspberry Pi system metric readers for pip-pi."""

import shutil
import time


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def parse_cpu_snapshot():
    line = read_text("/proc/stat")
    if not line:
        return None
    first = line.splitlines()[0].split()
    if len(first) < 8 or first[0] != "cpu":
        return None
    vals = [int(x) for x in first[1:8]]
    idle = vals[3] + vals[4]
    total = sum(vals)
    return total, idle


def read_cpu_percent(cache):
    snap = parse_cpu_snapshot()
    if snap is None:
        return cache.get("cpu", 0)

    prev = cache.get("cpu_prev")
    if prev is None:
        # First sample: take a short second snapshot to compute a real percentage.
        time.sleep(0.08)
        snap2 = parse_cpu_snapshot()
        if snap2 is None:
            cache["cpu_prev"] = snap
            return cache.get("cpu", 0)
        total_delta = snap2[0] - snap[0]
        idle_delta = snap2[1] - snap[1]
        cache["cpu_prev"] = snap2
        if total_delta <= 0:
            return cache.get("cpu", 0)
        cpu = _clamp(int(100.0 * (1.0 - (idle_delta / float(total_delta)))), 0, 100)
        cache["cpu"] = cpu
        return cpu

    cache["cpu_prev"] = snap

    total_delta = snap[0] - prev[0]
    idle_delta = snap[1] - prev[1]
    if total_delta <= 0:
        return cache.get("cpu", 0)
    cpu = _clamp(int(100.0 * (1.0 - (idle_delta / float(total_delta)))), 0, 100)
    cache["cpu"] = cpu
    return cpu


def read_mem_percent():
    meminfo = read_text("/proc/meminfo")
    if not meminfo:
        return None

    vals = {}
    for line in meminfo.splitlines():
        parts = line.split(":", 1)
        if len(parts) != 2:
            continue
        key = parts[0]
        try:
            vals[key] = int(parts[1].strip().split()[0])
        except Exception:
            continue

    total = vals.get("MemTotal")
    avail = vals.get("MemAvailable")
    if not total or avail is None:
        return None
    used = 100.0 * (1.0 - (avail / float(total)))
    return _clamp(int(used), 0, 100)


def read_storage_percent():
    try:
        usage = shutil.disk_usage("/")
        if usage.total <= 0:
            return None
        return _clamp(int(100.0 * (usage.used / float(usage.total))), 0, 100)
    except Exception:
        return None


def read_temp_c():
    # Standard Pi thermal sensor path.
    raw = read_text("/sys/class/thermal/thermal_zone0/temp")
    if raw:
        try:
            return float(raw) / 1000.0
        except Exception:
            pass
    return None


def read_uptime_str():
    txt = read_text("/proc/uptime")
    if txt:
        try:
            elapsed = int(float(txt.split()[0]))
            hh = elapsed // 3600
            mm = (elapsed % 3600) // 60
            return f"{hh:01d}:{mm:02d}"
        except Exception:
            pass

    return None
