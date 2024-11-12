import anyio
import structlog
from anyio.streams.memory import MemoryObjectReceiveStream

from jellbrid.clients.jellyfin import JellyfinClient
from jellbrid.clients.realdebrid import RealDebridClient
from jellbrid.clients.seers import SeerrsClient, get_requests
from jellbrid.clients.torrentio import TorrentioClient
from jellbrid.config import Config
from jellbrid.logging import setup_logging
from jellbrid.requests import EpisodeRequest, MovieRequest, RequestCache, SeasonRequest
from jellbrid.storage import SqliteRequestRepo, create_db, get_session
from jellbrid.sync import Synchronizer
from jellbrid.tasks import (
    handle_episode_request,
    handle_movie_request,
    handle_season_request,
    periodic_send,
    start_server,
    update_active_downloads,
    update_media,
)

logger = structlog.get_logger("jellbrid")


async def handle_requests(
    repo: SqliteRequestRepo,
    rdbc: RealDebridClient,
    seerrs: SeerrsClient,
    jc: JellyfinClient,
    tc: TorrentioClient,
    sync: Synchronizer,
    rc: RequestCache,
):
    async with sync.processing_lock:
        cfg = Config()
        logger.info("Starting request handling")
        async with anyio.create_task_group() as tg:
            async for request in get_requests(seerrs, jc):
                with structlog.contextvars.bound_contextvars(
                    **request.ctx, dev_mode=cfg.dev_mode
                ):
                    if request.imdb_id == "":
                        logger.warning("Unable to find IMDB for request")
                        continue
                    if cfg.tmdb_id is not None and request.tmdb_id != cfg.tmdb_id:
                        logger.debug("Skipping non-matching TMDB ID")
                        continue
                    match request:
                        case MovieRequest():
                            tg.start_soon(
                                handle_movie_request, request, tc, rdbc, sync, repo, rc
                            )
                        case SeasonRequest():
                            tg.start_soon(
                                handle_season_request,
                                request,
                                tc,
                                rdbc,
                                sync,
                                repo,
                                rc,
                                True,
                            )
                        case EpisodeRequest():
                            tg.start_soon(
                                handle_episode_request,
                                request,
                                tc,
                                rdbc,
                                sync,
                                repo,
                                rc,
                            )
                        case _:
                            logger.warning("Got unknown media type")
                    await anyio.sleep(1)

        if sync.refresh.is_set():
            await update_media(jc, seerrs)
            sync.reset()

        logger.info("Completed request handling")


async def run_receiver(r_stream: MemoryObjectReceiveStream):
    cfg = Config()
    if cfg.dev_mode:
        logger.warning("Running in dev-mode. Nothing will be downloaded")

    rdbc = RealDebridClient(cfg)
    tc = TorrentioClient(cfg)
    seerrs = SeerrsClient(cfg)
    jc = JellyfinClient(cfg)
    repo = SqliteRequestRepo(get_session())
    sync = Synchronizer(cfg)
    rc = RequestCache()

    async with anyio.create_task_group() as tg:
        async with r_stream:
            async for item in r_stream:
                if item == "process":
                    tg.start_soon(handle_requests, repo, rdbc, seerrs, jc, tc, sync, rc)
                if item == "update":
                    tg.start_soon(update_active_downloads, rdbc, repo, sync)


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
            tg.start_soon(start_server, send_stream.clone())
        else:
            async with send_stream:
                await send_stream.send("process")


if __name__ == "__main__":
    anyio.run(runit)
