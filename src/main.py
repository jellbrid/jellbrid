import typing as t

import anyio
import cachetools
import structlog

from jellbrid.clients.jellyfin import JellyfinClient, scan_and_wait_for_completion
from jellbrid.clients.realdebrid import RealDebridClient, RealDebridDownloader
from jellbrid.clients.seers import SeerrsClient, get_requests
from jellbrid.clients.torrentio import (
    TorrentioClient,
    get_streams_for_movie,
    get_streams_for_show,
)
from jellbrid.config import Config
from jellbrid.logging import setup_logging
from jellbrid.requests import EpisodeRequest, MediaType, MovieRequest, SeasonRequest
from jellbrid.storage import ActiveDownload, SqliteRequestRepo, create_db, get_session

logger = structlog.get_logger("jellbrid")


class Synchronizer:
    def __init__(self, cfg: Config):
        self.semaphore = anyio.Semaphore(cfg.n_parallel_requests)
        self.refresh = anyio.Event()
        self.cache = cachetools.Cache(100)

    def reset(self):
        self.refresh = anyio.Event()


async def handler(
    cfg: Config,
    *,
    repo: SqliteRequestRepo,
    rdbc: RealDebridClient,
    tc: TorrentioClient,
    sync: Synchronizer,
    tmdb_id: int | None = None,
):
    seers = SeerrsClient(cfg)
    jc = JellyfinClient(cfg)

    async with anyio.create_task_group() as tg:
        async for request in get_requests(seers, jc):
            with structlog.contextvars.bound_contextvars(
                **request.ctx, dev_mode=cfg.dev_mode
            ):
                if request.imdb_id == "":
                    logger.warning("Unable to find IMDB for request")
                    continue
                if tmdb_id is not None and request.tmdb_id != tmdb_id:
                    continue
                match request.type:
                    case MediaType.Movie:
                        tg.start_soon(
                            handle_movie_request,
                            t.cast(MovieRequest, request),
                            tc,
                            rdbc,
                            sync,
                            repo,
                        )
                    case MediaType.Season:
                        tg.start_soon(
                            handle_season_request,
                            t.cast(SeasonRequest, request),
                            tc,
                            rdbc,
                            sync,
                            repo,
                            True,
                        )
                    case MediaType.Episode:
                        tg.start_soon(
                            handle_episode_request,
                            t.cast(EpisodeRequest, request),
                            tc,
                            rdbc,
                            sync,
                            repo,
                        )
                    case _:
                        logger.warning("Got unknown media type")
                await anyio.sleep(1)

    await update_active_downloads(rdbc, repo, sync)

    if sync.refresh.is_set():
        logger.info("Sleeping to give ZURG time to pickup new files")
        await anyio.sleep(20)

        logger.info("Running library scan")
        if not cfg.dev_mode:
            await scan_and_wait_for_completion(jc)

        logger.info("Syncing requests with library")
        if not cfg.dev_mode:
            await seers.sync_with_jellyfin()

        logger.info("Sleeping to give requests time to update")
        await anyio.sleep(10)
        sync.reset()


async def handle_movie_request(
    request: MovieRequest,
    tc: TorrentioClient,
    rdbc: RealDebridClient,
    sync: Synchronizer,
    repo: SqliteRequestRepo,
):
    if await repo.has_movie(request.imdb_id):
        logger.debug("Ignoring currently downloading movie")
        return

    cache_key = request.imdb_id
    if cache_key in sync.cache:
        logger.debug("Ignoring already handled movie request")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        streams = await get_streams_for_movie(tc, request)
        rdd = RealDebridDownloader(rdbc, request=request, streams=streams)

        downloaded = await rdd.download_movie(await rdd.instantly_available_streams)
        if downloaded is not None:
            sync.refresh.set()
            sync.cache[cache_key] = True
            return

        # Look for a the highest quality stream with many seeders
        # TODO: sort the streams ourselves
        downloaded = await rdd.download_movie(await rdd.unavailable_streams)
        if downloaded is not None:
            ad = ActiveDownload.from_movie_request(request, downloaded)
            await repo.add(ad)
            sync.cache[cache_key] = True
            return

        logger.info("Unable to find any matching torrents")


async def handle_season_request(
    request: SeasonRequest,
    tc: TorrentioClient,
    rdbc: RealDebridClient,
    sync: Synchronizer,
    repo: SqliteRequestRepo,
    backoff_to_episodes: bool = False,
):
    if await repo.has_season(request.imdb_id, request.season_id):
        logger.debug("Ignoring currently downloading season")
        return

    cache_key = f"{request.imdb_id}-{request.season_id}"
    if cache_key in sync.cache:
        logger.debug("Ignoring already handled request for season")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        streams = await get_streams_for_show(tc, request)
        rdd = RealDebridDownloader(rdbc, request=request, streams=streams)
        downloaded = await rdd.download_show(await rdd.instantly_available_streams)
        if downloaded is not None:
            sync.refresh.set()
            sync.cache[cache_key] = True
            return

        logger.info("Unable to find any matching torrents")

    if backoff_to_episodes:
        logger.info("Searching for individual episodes")
        for er in request.to_episode_requests():
            with structlog.contextvars.bound_contextvars(**er.ctx):
                await handle_episode_request(er, tc, rdbc, sync, repo=repo)


async def handle_episode_request(
    request: EpisodeRequest,
    tc: TorrentioClient,
    rdbc: RealDebridClient,
    sync: Synchronizer,
    repo: SqliteRequestRepo,
):
    if await repo.has_episode(request.imdb_id, request.season_id, request.episode_id):
        logger.debug("Ignoring currently downloading episode")
        return

    cache_key = f"{request.imdb_id}-{request.season_id}-{request.episode_id}"
    if cache_key in sync.cache:
        logger.debug("Ignoring already handled request for episode")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        streams = await get_streams_for_show(tc, request)
        # search for a cached torrent with just the episode we want
        rdd = RealDebridDownloader(rdbc, request=request, streams=streams)
        downloaded = await rdd.download_episode(await rdd.instantly_available_streams)
        if downloaded is not None:
            sync.refresh.set()
            sync.cache[cache_key] = True
            return

        # search for the episode we want inside of a cached torrent
        downloaded = await rdd.download_episode_from_bundle(
            await rdd.instantly_available_streams
        )
        if downloaded is not None:
            ad = ActiveDownload.from_episode_request(request, torrent_id=downloaded)
            await repo.add(ad)
            sync.cache[cache_key] = True
            return

        # search for an uncached torrent with just the episode we want
        # TODO: sort the streams ourselves
        downloaded = await rdd.download_episode(await rdd.unavailable_streams)
        if downloaded is not None:
            ad = ActiveDownload.from_episode_request(request, torrent_id=downloaded)
            await repo.add(ad)
            sync.cache[cache_key] = True
            return

        logger.info("Unable to find any matching torrents")


async def update_active_downloads(
    rdbc: RealDebridClient, repo: SqliteRequestRepo, sync: Synchronizer
):
    for request in await repo.get_requests():
        info = await rdbc.get_torrent_files_info(request.torrent_id)
        if info["progress"] == 100:
            sync.refresh.set()
            await repo.delete(request)
        elif info["status"] in ("error", "dead"):
            await repo.delete(request)


async def runit(run_once: bool = True, tmdb_id: int | None = None):
    cfg = Config()
    await create_db(cfg)
    setup_logging(cfg.jellbrid_log_level)

    if cfg.dev_mode:
        logger.warning("Running in dev-mode. Nothing will be downloaded")
    else:
        logger.info("Beginning processing loop")

    # make these here to persist caches across runs
    rdbc = RealDebridClient(cfg)
    tc = TorrentioClient(cfg)
    repo = SqliteRequestRepo(get_session())
    sync = Synchronizer(cfg)

    while True:
        await handler(cfg, rdbc=rdbc, tc=tc, repo=repo, sync=sync, tmdb_id=tmdb_id)
        logger.info("Completed request processing")
        if run_once:
            break
        await anyio.sleep(60)


if __name__ == "__main__":
    anyio.run(runit)
