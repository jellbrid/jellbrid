import anyio
import structlog
from anyio.streams.memory import MemoryObjectSendStream
from hypercorn.asyncio import serve

from jellbrid.clients.jellyfin import JellyfinClient, scan_and_wait_for_completion
from jellbrid.clients.realdebrid import RealDebridClient, RealDebridDownloader
from jellbrid.clients.seers import SeerrsClient
from jellbrid.clients.torrentio import (
    TorrentioClient,
    get_streams_for_movie,
    get_streams_for_show,
)
from jellbrid.config import Config
from jellbrid.requests import EpisodeRequest, MovieRequest, RequestCache, SeasonRequest
from jellbrid.storage import ActiveDownload, SqliteRequestRepo
from jellbrid.sync import Synchronizer
from server import app, get_server_config

logger = structlog.get_logger(__name__)


async def periodic_send(stream: MemoryObjectSendStream, message: str, period: int = 60):
    while True:
        await stream.send(message)
        await anyio.sleep(period)


async def update_active_downloads(
    rdbc: RealDebridClient,
    repo: SqliteRequestRepo,
    sync: Synchronizer,
    seerrs: SeerrsClient,
    jc: JellyfinClient,
):
    async with sync.processing_lock:
        for request in await repo.get_requests():
            info = await rdbc.get_torrent_files_info(request.torrent_id)
            if info["progress"] == 100:
                sync.refresh.set()
                await repo.delete(request)
            elif info["status"] in ("error", "dead"):
                logger.warning("Unable to process torrent")
                await repo.delete(request)

        if sync.refresh.is_set():
            await update_media(jc, seerrs)
            sync.reset()


async def handle_movie_request(
    request: MovieRequest,
    tc: TorrentioClient,
    rdbc: RealDebridClient,
    sync: Synchronizer,
    repo: SqliteRequestRepo,
    rc: RequestCache,
):
    if await repo.has_movie(request.imdb_id):
        logger.debug("Ignoring currently downloading movie")
        return

    if rc.has_request(request):
        logger.debug("Ignoring already handled movie request")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        streams = await get_streams_for_movie(tc, request)
        rdd = RealDebridDownloader(rdbc, request=request, streams=streams)

        downloaded = await rdd.download_movie()
        if downloaded is not None:
            ad = ActiveDownload.from_movie_request(request, downloaded)
            await repo.add(ad)
            rc.add_request(request)
            return

        logger.info("Unable to find any matching torrents")


async def handle_season_request(
    request: SeasonRequest,
    tc: TorrentioClient,
    rdbc: RealDebridClient,
    sync: Synchronizer,
    repo: SqliteRequestRepo,
    rc: RequestCache,
    backoff_to_episodes: bool = False,
):
    if await repo.has_season(request.imdb_id, request.season_id):
        logger.debug("Ignoring currently downloading season")
        return

    if rc.has_request(request):
        logger.debug("Ignoring already handled request for season")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        streams = await get_streams_for_show(tc, request)
        rdd = RealDebridDownloader(rdbc, request=request, streams=streams)
        downloaded = await rdd.download_show()
        if downloaded is not None:
            ad = ActiveDownload.from_season_request(request, downloaded)
            await repo.add(ad)
            rc.add_request(request)
            return

        logger.info("Unable to find any matching torrents")

    if backoff_to_episodes:
        logger.info("Searching for individual episodes")
        for er in request.to_episode_requests():
            with structlog.contextvars.bound_contextvars(**er.ctx):
                await handle_episode_request(er, tc, rdbc, sync, repo=repo, rc=rc)


async def handle_episode_request(
    request: EpisodeRequest,
    tc: TorrentioClient,
    rdbc: RealDebridClient,
    sync: Synchronizer,
    repo: SqliteRequestRepo,
    rc: RequestCache,
):
    if await repo.has_episode(request.imdb_id, request.season_id, request.episode_id):
        logger.debug("Ignoring currently downloading episode")
        return

    if rc.has_request(request):
        logger.debug("Ignoring already handled request for episode")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        streams = await get_streams_for_show(tc, request)
        rdd = RealDebridDownloader(rdbc, request=request, streams=streams)

        # search for a cached torrent with just the episode we want
        downloaded = await rdd.download_episode()

        if downloaded is None:
            # search for the episode we want inside of a cached torrent
            downloaded = await rdd.download_episode_from_bundle()

        if downloaded is not None:
            ad = ActiveDownload.from_episode_request(request, downloaded)
            await repo.add(ad)
            rc.add_request(request)
            return

        logger.info("Unable to find any matching torrents")


async def update_media(jc: JellyfinClient, seerrs: SeerrsClient):
    cfg = Config()
    logger.info("Sleeping to give ZURG time to pickup new files")
    if not cfg.dev_mode:
        await anyio.sleep(20)

    logger.info("Running library scan")
    if not cfg.dev_mode:
        await scan_and_wait_for_completion(jc)

    logger.info("Syncing requests with library")
    if not cfg.dev_mode:
        await seerrs.sync_with_jellyfin()

    logger.info("Sleeping to give requests time to update")
    if not cfg.dev_mode:
        await anyio.sleep(10)


async def start_server(send_stream: MemoryObjectSendStream):
    app.send_stream = send_stream  # type:ignore
    await serve(app, get_server_config())
