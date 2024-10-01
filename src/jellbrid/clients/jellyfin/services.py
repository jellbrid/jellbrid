import anyio

from jellbrid.clients.jellyfin.client import JellyfinClient
from jellbrid.clients.jellyfin.types import TaskState


async def scan_and_wait_for_completion(jfc: JellyfinClient, *, interval: int = 30):
    await jfc.refresh_library()

    task = await jfc.get_media_scan_task()
    if task is None:
        return

    scan_task_id = task["Id"]
    while task["State"] == TaskState.Running.value:
        await anyio.sleep(interval)
        task = await jfc.get_task_by_id(scan_task_id)
