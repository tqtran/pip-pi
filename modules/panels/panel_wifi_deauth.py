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


def render_status(screen, rect, fonts, now, *, text_surf, S, color):
    """Render deauth status lines scrolling upward, newest at bottom."""
    with _STATUS_LOCK:
        lines = list(_STATUS_LINES)

    if not lines:
        lines = ["deauth simulation idle"]

    prev_clip = screen.get_clip()
    screen.set_clip(rect)

    line_h = fonts["sm"].get_height() + 2
    max_visible = max(1, rect.h // line_h)
    visible = lines[-max_visible:]

    # Pin newest line to bottom, older lines above
    for i, line in enumerate(reversed(visible)):
        y = rect.bottom - (i + 1) * line_h
        if y < rect.y:
            break
        surf = text_surf(fonts["sm"], line, color)
        clipped_w = min(surf.get_width(), rect.w - S(4))
        screen.blit(surf.subsurface((0, 0, clipped_w, surf.get_height())), (rect.x + S(4), y))

    screen.set_clip(prev_clip)
