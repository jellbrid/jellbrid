from rich.pretty import pprint

from jellbrid.cli.base import AsyncTyper
from jellbrid.clients.jellyfin import JellyfinClient, scan_and_wait_for_completion
from jellbrid.config import Config

app = AsyncTyper()


@app.command()
async def refresh():
    jfc = JellyfinClient(Config())
    await jfc.refresh_library()


@app.command()
async def get_episodes(id: str):
    jfc = JellyfinClient(Config())
    result = await jfc.get_episodes_in_season(id)
    pprint(result)


@app.command()
async def get_scan():
    jfc = JellyfinClient(Config())
    task = await jfc.get_media_scan_task()
    pprint(task)


@app.command()
async def scan_wait():
    jfc = JellyfinClient(Config())
    await scan_and_wait_for_completion(jfc, interval=5)
