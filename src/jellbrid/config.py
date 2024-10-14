import logging
from pathlib import Path

import environs


class Config:
    def __init__(self):
        env = environs.Env()
        env.read_env()

        self.rd_api_key: str = env("RD_API_KEY")
        self.jf_api_key: str = env("JF_API_KEY")
        self.jf_url: str = env.url("JF_URL").geturl()
        self.seerr_api_key = env("SEERR_API_KEY")
        self.seerr_url = env.url("SEERR_URL").geturl()
        self.torrentio_url = env.url("TORRENTIO_URL").geturl()
        self.rd_api_url = env.url("RD_API_URL").geturl()
        self.jellbrid_log_level: int = env.log_level(
            "JELLBRID_LOG_LEVEL", default=logging.DEBUG
        )
        self.dev_mode: bool = env.bool("DEV_MODE", default=True)
        self.n_parallel_requests: int = env.int(
            "N_PARALLEL_REQUESTS", default=1 if self.dev_mode else 3
        )
        self.storage_dir = Path.home() / ".config/jellbrid"
        Path.mkdir(self.storage_dir, exist_ok=True)
        self.db = self.storage_dir / "jellbrid.db"

        self.server_port = env.int("JELLBRID_SERVER_PORT", default=9090)
        self.tmdb_id: int | None = env.int("JELLBRID_TMDBID", default=None)
