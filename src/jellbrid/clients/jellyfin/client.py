import typing as t

import structlog

from jellbrid.clients.base import BaseClient
from jellbrid.clients.jellyfin.types import Task
from jellbrid.config import Config

logger = structlog.get_logger(__name__)


class JellyfinClient:
    def __init__(self, cfg: Config):
        self.client = BaseClient(
            cfg.jf_url, {"Authorization": f"MediaBrowser Token={cfg.jf_api_key}"}
        )
        self.cfg = cfg

    async def get_system_info(self):
        return await self.client.request("GET", "System/Info")

    async def refresh_library(self):
        await self.client.request("POST", "Library/Refresh")

    async def get_scheduled_tasks(self) -> list[Task]:
        result = await self.client.request("GET", "ScheduledTasks")
        return t.cast(list[Task], result)

    async def get_task_by_id(self, id: str) -> Task:
        result = await self.client.request("GET", f"ScheduledTasks/{id}")
        return t.cast(Task, result)

    async def get_media_scan_task(self) -> Task | None:
        tasks = await self.get_scheduled_tasks()
        for task in tasks:
            if task["Name"] == "Scan Media Library":
                return task
        return None

    async def get_episodes_in_season(
        self, media_id: str, season: int | None = None
    ) -> list[dict]:
        params = {"season": season} if season else None
        result = await self.client.request(
            "GET", f"Shows/{media_id}/Episodes", params=params
        )
        return result["Items"]
