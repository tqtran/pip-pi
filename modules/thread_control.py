import threading


_THREADS_LOCK = threading.Lock()
_TRACKED_THREADS = {}
_SHUTDOWN_EVENT = threading.Event()


def get_shutdown_event():
    return _SHUTDOWN_EVENT


def is_shutting_down():
    return _SHUTDOWN_EVENT.is_set()


def request_shutdown():
    _SHUTDOWN_EVENT.set()


def start_managed_thread(name, target, args=(), kwargs=None, daemon=True):
    if kwargs is None:
        kwargs = {}

    if _SHUTDOWN_EVENT.is_set():
        return None

    holder = {}

    def _runner():
        try:
            target(*args, **kwargs)
        finally:
            thread = holder.get("thread")
            if thread is not None:
                with _THREADS_LOCK:
                    _TRACKED_THREADS.pop(id(thread), None)

    thread = threading.Thread(name=name, target=_runner, daemon=daemon)
    holder["thread"] = thread
    with _THREADS_LOCK:
        _TRACKED_THREADS[id(thread)] = thread
    thread.start()
    return thread


def stop_all_background_threads(timeout_per_thread=2.0):
    _SHUTDOWN_EVENT.set()

    with _THREADS_LOCK:
        threads = [t for t in _TRACKED_THREADS.values() if t is not threading.current_thread()]

    for thread in threads:
        if thread.is_alive():
            thread.join(timeout=max(0.0, float(timeout_per_thread)))

    with _THREADS_LOCK:
        return [t.name for t in _TRACKED_THREADS.values() if t.is_alive() and t is not threading.current_thread()]
