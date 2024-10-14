import anyio

from jellbrid.config import Config


class Synchronizer:
    def __init__(self, cfg: Config):
        self.semaphore = anyio.Semaphore(cfg.n_parallel_requests)
        self.refresh = anyio.Event()
        self.update_lock = anyio.Lock()

    def reset(self):
        self.refresh = anyio.Event()
