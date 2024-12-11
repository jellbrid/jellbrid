import anyio
import structlog
from anyio.streams.memory import MemoryObjectReceiveStream

from jellbrid.clients.jellyfin import JellyfinClient
from jellbrid.clients.realdebrid import RealDebridClient
from jellbrid.clients.seers import SeerrsClient
from jellbrid.clients.torrentio import TorrentioClient
from jellbrid.config import Config
from jellbrid.logging import setup_logging
from jellbrid.requests import RequestCache
from jellbrid.storage import ActiveDownloadRepo, BadHashRepo, create_db, get_session
from jellbrid.sync import Synchronizer
from jellbrid.tasks import (
    clear_stalled_downloads,
    handle_requests,
    periodic_send,
    start_server,
    update_active_downloads,
)

logger = structlog.get_logger("jellbrid")


async def run_receiver(r_stream: MemoryObjectReceiveStream):
    cfg = Config()
    if cfg.dev_mode:
        logger.warning("Running in dev-mode. Nothing will be downloaded")

    rdbc = RealDebridClient(cfg)
    tc = TorrentioClient(cfg)
    seerrs = SeerrsClient(cfg)
    jc = JellyfinClient(cfg)
    dl_repo = ActiveDownloadRepo(get_session())
    hash_repo = BadHashRepo(get_session())
    sync = Synchronizer(cfg)
    rc = RequestCache()

    async with anyio.create_task_group() as tg:
        async with r_stream:
            async for item in r_stream:
                if item == "process":
                    tg.start_soon(
                        handle_requests, dl_repo, rdbc, seerrs, jc, tc, sync, rc
                    )
                if item == "update":
                    tg.start_soon(
                        update_active_downloads, rdbc, dl_repo, sync, seerrs, jc
                    )
                if item == "clear_stalled":
                    tg.start_soon(clear_stalled_downloads, rdbc, dl_repo, hash_repo, 3)


async def runit(loop: bool = True):
    cfg = Config()
    await create_db(cfg)
    setup_logging(cfg.jellbrid_log_level)

    send_stream, receive_stream = anyio.create_memory_object_stream[str]()
    async with anyio.create_task_group() as tg:
        tg.start_soon(run_receiver, receive_stream)

        if loop:
            tg.start_soon(periodic_send, send_stream.clone(), "process", 60 * 10)
            tg.start_soon(periodic_send, send_stream.clone(), "update", 60 * 5)
            tg.start_soon(periodic_send, send_stream.clone(), "clear_stalled", 60 * 5)
            tg.start_soon(start_server, send_stream.clone())
        else:
            async with send_stream:
                await send_stream.send("process")


if __name__ == "__main__":
    anyio.run(runit)
