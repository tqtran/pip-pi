#!/usr/bin/env python3
"""Configuration lifecycle for pip-pi.

Handles defaults, legacy migration, loading, and writing config files.
"""

import json
import os

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "pip-pi.config.json")
LEGACY_CONFIG_PATH = os.path.join(PROJECT_ROOT, "pip-pi.config.json")

DEFAULT_CONFIG = {
    "scan_intervals": {
        "ble_seconds": 60.0,
        "wifi_seconds": 60.0,
    },
    "scan_behavior": {
        "ble_first_window_seconds": 60.0,
        "ble_window_seconds": 15.0,
        "ble_stagger_seconds": 30.0,
    },
    "refresh_intervals": {
        "load_seconds": 5.0,
        "stats_seconds": 60.0,
    },
}


def clone_default_config():
    return {
        "scan_intervals": {
            "ble_seconds": DEFAULT_CONFIG["scan_intervals"]["ble_seconds"],
            "wifi_seconds": DEFAULT_CONFIG["scan_intervals"]["wifi_seconds"],
        },
        "scan_behavior": {
            "ble_first_window_seconds": DEFAULT_CONFIG["scan_behavior"]["ble_first_window_seconds"],
            "ble_window_seconds": DEFAULT_CONFIG["scan_behavior"]["ble_window_seconds"],
            "ble_stagger_seconds": DEFAULT_CONFIG["scan_behavior"]["ble_stagger_seconds"],
        },
        "refresh_intervals": {
            "load_seconds": DEFAULT_CONFIG["refresh_intervals"]["load_seconds"],
            "stats_seconds": DEFAULT_CONFIG["refresh_intervals"]["stats_seconds"],
        },
    }


def merge_config_with_defaults(cfg):
    """Return runtime config with all expected keys present."""
    merged = clone_default_config()
    if not isinstance(cfg, dict):
        return merged

    for section in ("scan_intervals", "scan_behavior", "refresh_intervals"):
        src = cfg.get(section)
        if not isinstance(src, dict):
            continue
        for key, val in src.items():
            if key in merged[section]:
                merged[section][key] = val
    return merged


def write_config_file(cfg):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, sort_keys=True)


def maybe_migrate_legacy_config():
    if os.path.exists(CONFIG_PATH) or not os.path.exists(LEGACY_CONFIG_PATH):
        return
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.replace(LEGACY_CONFIG_PATH, CONFIG_PATH)
        print(f"[config] moved legacy config to {CONFIG_PATH}")
    except Exception as exc:
        print(f"[config] failed to migrate legacy config: {exc}")


def load_config():
    maybe_migrate_legacy_config()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                return merge_config_with_defaults(cfg)
            print(f"[config] invalid root type in {CONFIG_PATH}; using defaults")
        except Exception as exc:
            print(f"[config] failed to read {CONFIG_PATH}: {exc}; using defaults")

    cfg = clone_default_config()
    try:
        write_config_file(cfg)
        print(f"[config] wrote default config: {CONFIG_PATH}")
    except Exception as exc:
        print(f"[config] failed to write default config {CONFIG_PATH}: {exc}")
    return merge_config_with_defaults(cfg)


CONFIG = load_config()
