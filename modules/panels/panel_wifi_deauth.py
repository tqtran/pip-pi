import threading
import time
from collections import deque

_STATUS_LINES = deque(maxlen=120)
_STATUS_LOCK = threading.Lock()
_WORKER_LOCK = threading.Lock()
_WORKER_STARTED = False
_WORKER_STOP_EVENT = None
_WORKER_THREAD = None


def _push_status(message):
    with _STATUS_LOCK:
        _STATUS_LINES.append(str(message))


def begin_deauth(ap_mac, target_mac, interface):
    """Start a safe simulated deauth status stream (no packet transmission)."""
    global _WORKER_STARTED, _WORKER_STOP_EVENT, _WORKER_THREAD

    with _WORKER_LOCK:
        if _WORKER_STARTED:
            _push_status("simulation already running")
            return False
        stop_event = threading.Event()
        _WORKER_STOP_EVENT = stop_event
        _WORKER_STARTED = True

    def _worker():
        try:
            _push_status(f"starting simulation ap={ap_mac} target={target_mac} iface={interface}")
            while not stop_event.wait(1.0):
                stamp = time.strftime("%Y-%m-%d %H:%M:%S")
                _push_status(f"{stamp} deauth simulation active ap={ap_mac} target={target_mac} iface={interface}")
        finally:
            with _WORKER_LOCK:
                global _WORKER_STARTED, _WORKER_STOP_EVENT, _WORKER_THREAD
                if _WORKER_STOP_EVENT is stop_event:
                    _WORKER_STOP_EVENT = None
                _WORKER_THREAD = None
                _WORKER_STARTED = False
            _push_status("simulation stopped")

    worker = threading.Thread(target=_worker, daemon=True)
    with _WORKER_LOCK:
        _WORKER_THREAD = worker
    worker.start()
    return True


def stop_deauth():
    """Stop the simulated deauth status stream."""
    global _WORKER_STARTED

    with _WORKER_LOCK:
        if not _WORKER_STARTED:
            _push_status("simulation already stopped")
            return False
        _WORKER_STARTED = False
        stop_event = _WORKER_STOP_EVENT

    _push_status("stopping simulation")
    if stop_event is not None:
        stop_event.set()
    return True


def render_status(screen, rect, fonts, now, *, text_surf, color):
    """Render latest deauth status as scrolling marquee text inside rect."""
    with _STATUS_LOCK:
        lines = list(_STATUS_LINES)

    if not lines:
        status_text = "deauth simulation idle"
    else:
        status_text = " | ".join(lines[-8:])

    surf = text_surf(fonts["sm"], status_text, color)

    prev_clip = screen.get_clip()
    screen.set_clip(rect)

    if surf.get_width() <= rect.w:
        x = rect.x + 4
        y = rect.y + (rect.h - surf.get_height()) // 2
        screen.blit(surf, (x, y))
    else:
        speed_px_s = 70.0
        gap = 80
        cycle = surf.get_width() + gap
        offset = int((now * speed_px_s) % cycle)
        x1 = rect.x + 4 - offset
        y = rect.y + (rect.h - surf.get_height()) // 2
        screen.blit(surf, (x1, y))
        screen.blit(surf, (x1 + cycle, y))

    screen.set_clip(prev_clip)
