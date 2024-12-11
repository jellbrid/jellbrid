import datetime

import anyio
import structlog
from anyio.streams.memory import MemoryObjectSendStream
from hypercorn.asyncio import serve
from zoneinfo import ZoneInfo

from jellbrid.clients.jellyfin import JellyfinClient, scan_and_wait_for_completion
from jellbrid.clients.realdebrid import (
    RealDebridClient,
    RealDebridDownloader,
    TorrentStatus,
)
from jellbrid.clients.seers import SeerrsClient, get_requests
from jellbrid.clients.torrentio import (
    TorrentioClient,
    get_streams_for_movie,
    get_streams_for_show,
)
from jellbrid.config import Config
from jellbrid.requests import EpisodeRequest, MovieRequest, RequestCache, SeasonRequest
from jellbrid.storage import ActiveDownload, ActiveDownloadRepo, BadHash, BadHashRepo
from jellbrid.sync import Synchronizer
from server import app, get_server_config

logger = structlog.get_logger(__name__)


async def start_server(send_stream: MemoryObjectSendStream):
    app.send_stream = send_stream  # type:ignore
    await serve(app, get_server_config())


async def periodic_send(stream: MemoryObjectSendStream, message: str, period: int = 60):
    while True:
        await stream.send(message)
        await anyio.sleep(period)


async def handle_movie_request(
    request: MovieRequest,
    tc: TorrentioClient,
    rdbc: RealDebridClient,
    sync: Synchronizer,
    dl_repo: ActiveDownloadRepo,
    hash_repo: BadHashRepo,
    rc: RequestCache,
):
    if await dl_repo.has_movie(request.imdb_id):
        logger.debug("Ignoring currently downloading movie")
        return

    if rc.has_request(request):
        logger.debug("Ignoring already handled movie request")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        streams = await get_streams_for_movie(tc, request)
        rdd = RealDebridDownloader(
            rdbc, hash_repo=hash_repo, request=request, streams=streams
        )

        downloaded = await rdd.download_movie()
        if downloaded is not None:
            ad = ActiveDownload.from_movie_request(request, downloaded)
            await dl_repo.add(ad)
            rc.add_request(request)
            return

        logger.info("Unable to find any matching torrents")


async def handle_season_request(
    request: SeasonRequest,
    tc: TorrentioClient,
    rdbc: RealDebridClient,
    sync: Synchronizer,
    dl_repo: ActiveDownloadRepo,
    hash_repo: BadHashRepo,
    rc: RequestCache,
    backoff_to_episodes: bool = False,
):
    if await dl_repo.has_season(request.imdb_id, request.season_id):
        logger.debug("Ignoring currently downloading season")
        return

    if rc.has_request(request):
        logger.debug("Ignoring already handled request for season")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        streams = await get_streams_for_show(tc, request)
        rdd = RealDebridDownloader(
            rdbc, hash_repo=hash_repo, request=request, streams=streams
        )
        downloaded = await rdd.download_show()
        if downloaded is not None:
            ad = ActiveDownload.from_season_request(request, downloaded)
            await dl_repo.add(ad)
            rc.add_request(request)
            return

        logger.info("Unable to find any matching torrents")

    if backoff_to_episodes:
        logger.info("Searching for individual episodes")
        for er in request.to_episode_requests():
            with structlog.contextvars.bound_contextvars(**er.ctx):
                await handle_episode_request(
                    er, tc, rdbc, sync, dl_repo=dl_repo, hash_repo=hash_repo, rc=rc
                )


async def handle_episode_request(
    request: EpisodeRequest,
    tc: TorrentioClient,
    rdbc: RealDebridClient,
    sync: Synchronizer,
    dl_repo: ActiveDownloadRepo,
    hash_repo: BadHashRepo,
    rc: RequestCache,
):
    if await dl_repo.has_episode(
        request.imdb_id, request.season_id, request.episode_id
    ):
        logger.debug("Ignoring currently downloading episode")
        return

    if rc.has_request(request):
        logger.debug("Ignoring already handled request for episode")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        streams = await get_streams_for_show(tc, request)
        rdd = RealDebridDownloader(
            rdbc, hash_repo=hash_repo, request=request, streams=streams
        )

        # search for a cached torrent with just the episode we want
        downloaded = await rdd.download_episode()

        if downloaded is None:
            # search for the episode we want inside of a cached torrent
            downloaded = await rdd.download_episode_from_bundle()

        if downloaded is not None:
            ad = ActiveDownload.from_episode_request(request, downloaded)
            await dl_repo.add(ad)
            rc.add_request(request)
            return

        logger.info("Unable to find any matching torrents")


async def update_active_downloads(
    rdbc: RealDebridClient,
    repo: ActiveDownloadRepo,
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


async def handle_requests(
    dl_repo: ActiveDownloadRepo,
    hash_repo: BadHashRepo,
    rdbc: RealDebridClient,
    seerrs: SeerrsClient,
    jc: JellyfinClient,
    tc: TorrentioClient,
    sync: Synchronizer,
    rc: RequestCache,
):
    async with sync.processing_lock:
        cfg = Config()
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
                                handle_movie_request,
                                request,
                                tc,
                                rdbc,
                                sync,
                                dl_repo,
                                hash_repo,
                                rc,
                            )
                        case SeasonRequest():
                            tg.start_soon(
                                handle_season_request,
                                request,
                                tc,
                                rdbc,
                                sync,
                                dl_repo,
                                hash_repo,
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
                                dl_repo,
                                hash_repo,
                                rc,
                            )
                        case _:
                            logger.warning("Got unknown media type")
                    await anyio.sleep(1)

    await update_active_downloads(rdbc, dl_repo, sync, seerrs, jc)


async def clear_stalled_downloads(
    rdbc: RealDebridClient,
    dl_repo: ActiveDownloadRepo,
    hash_repo: BadHashRepo,
    limit_hrs: int = 3,
):
    """
    Read active downloads and remove any that have been active for more than
    limit_hrs. This will track the problematic hash, and clear the download from
    RD and the internal download tracker
    """
    logger.info("Checking for stalled downloads")

    now = datetime.datetime.now(datetime.timezone.utc)
    limit_seconds = limit_hrs * 60 * 60
    active_downloads = await rdbc.get_torrents(status=TorrentStatus.DOWNLOADING)

    for download in active_downloads:
        # update the timezone to be accurate...
        added_at = download["added"].strip("Z")
        dt = datetime.datetime.fromisoformat(added_at).replace(
            tzinfo=ZoneInfo("Europe/Paris")
        )
        if (now - dt).total_seconds() < limit_seconds:
            continue

        logger.info(
            f"Deleting stalled download older than {limit_hrs}hr(s)",
            id=download["id"],
            hash=download["hash"],
            added_at=str(dt),
        )

        bad_hash = BadHash(
            hash=download["hash"],
            filename=download["filename"],
            progress=download["progress"],
            status=download["status"],
        )
        await hash_repo.add(bad_hash)
        await dl_repo.delete_by_did(download["id"])
        await rdbc.delete_magnet(download["id"])
