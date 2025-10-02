import threading
from queue import Queue

class TaskManager:
    def __init__(self, root, max_workers=3):
        self.root = root
        self.task_queue = Queue()
        self.parallel_queue = Queue()
        self.running = False
        self.active_threads = set()
        self.max_workers = max_workers

    def add_task(self, func, *args, threaded=False, on_done=None, **kwargs):
        """Add a sequential task to the queue with optional on_done callback."""
        self.task_queue.put((func, args, kwargs, threaded, on_done))
        if not self.running:
            self.root.after(50, self.run_next)

    def run_next(self):
        if not self.task_queue.empty():
            self.running = True
            func, args, kwargs, threaded, on_done = self.task_queue.get()

            if threaded:
                t = threading.Thread(target=self._run_sequential_task,
                                     args=(func, args, kwargs, on_done),
                                     daemon=True)
                t.start()
            else:
                self._run_sequential_task(func, args, kwargs, on_done)
        else:
            self.running = False

    def _run_sequential_task(self, func, args, kwargs, on_done):
        result = func(*args, **kwargs)
        if on_done:
            self.root.after(0, lambda: on_done(result))
        self.root.after(50, self.run_next)

    def add_parallel_task(self, func, *args, on_done=None, **kwargs):
        """Queue a parallel task. Scheduler will run it if workers available."""
        self.parallel_queue.put((func, args, kwargs, on_done))
        self._schedule_next_parallel()

    def _schedule_next_parallel(self):
        """Start next parallel task if workers available."""
        while len(self.active_threads) < self.max_workers and not self.parallel_queue.empty():
            func, args, kwargs, on_done = self.parallel_queue.get()

            def wrapper():
                try:
                    result = func(*args, **kwargs)
                    if on_done:
                        self.root.after(0, lambda: on_done(result))
                finally:
                    self.active_threads.discard(threading.current_thread())
                    self.root.after(10, self._schedule_next_parallel)

            t = threading.Thread(target=wrapper, daemon=True)
            self.active_threads.add(t)
            t.start()

    def is_busy(self):
        return self.running or bool(self.active_threads) or not self.parallel_queue.empty()
