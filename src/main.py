import typing as t

import anyio
import cachetools
import structlog
from cachetools import Cache

from jellbrid.clients.jellyfin import JellyfinClient, scan_and_wait_for_completion
from jellbrid.clients.realdebrid import RealDebridClient, RealDebridDownloader
from jellbrid.clients.seers import SeerrsClient, get_requests
from jellbrid.clients.torrentio import QualityFilter, SortOrder, TorrentioClient
from jellbrid.config import Config
from jellbrid.logging import setup_logging
from jellbrid.requests import EpisodeRequest, MediaType, MovieRequest, SeasonRequest

logger = structlog.get_logger("jellbrid")


class Synchronizer:
    def __init__(self, cfg: Config):
        self.semaphore = anyio.Semaphore(cfg.n_parallel_requests)
        self.refresh = anyio.Event()

    def reset(self):
        self.refresh = anyio.Event()


async def handler(
    cfg: Config,
    *,
    rdbc: RealDebridClient,
    tc: TorrentioClient,
    cache: Cache,
    tmdb_id: int | None = None,
):
    seers = SeerrsClient(cfg)
    jc = JellyfinClient(cfg)
    sync = Synchronizer(cfg)

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
                            cache,
                        )
                    case MediaType.Season:
                        tg.start_soon(
                            handle_season_request,
                            t.cast(SeasonRequest, request),
                            tc,
                            rdbc,
                            sync,
                            cache,
                            True,
                        )
                    case MediaType.Episode:
                        tg.start_soon(
                            handle_episode_request,
                            t.cast(EpisodeRequest, request),
                            tc,
                            rdbc,
                            sync,
                            cache,
                        )
                    case _:
                        logger.warning("Got unknown media type")
                await anyio.sleep(1)

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
    cache: Cache,
):
    if request.imdb_id in cache:
        logger.debug("Ignoring cached request")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        # Look for the highest quality, instantly available stream
        if tc.is_older_media(request.release_year):
            filter = QualityFilter.OLD
            sort = SortOrder.SEEDERS
        else:
            filter = QualityFilter.HD
            sort = SortOrder.QUALITY_THEN_SIZE

        streams = await tc.get_movie_streams(
            request.imdb_id, filter=filter, sort_order=sort
        )
        rdd = RealDebridDownloader(rdbc, request=request, streams=streams)

        downloaded = await rdd.download_movie(await rdd.instantly_available_streams)
        if downloaded:
            sync.refresh.set()
            return

        # Look for a the highest quality stream with many seeders
        # only perform the search if we previously got any results at all
        # TODO: remove cached streams from this, sort the streams ourselves
        downloaded = await rdd.download_movie(await rdd.unavailable_streams)
        if downloaded:
            sync.refresh.set()
            cache[request.imdb_id] = True
            return

        logger.info("Unable to find any matching torrents")


async def handle_season_request(
    request: SeasonRequest,
    tc: TorrentioClient,
    rdbc: RealDebridClient,
    sync: Synchronizer,
    cache: Cache,
    backoff_to_episodes: bool = False,
):
    if request.imdb_id in cache:
        logger.debug("Ignoring cached request")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        if tc.is_older_media(request.release_year):
            filter = QualityFilter.OLD
            sort = SortOrder.SEEDERS
        else:
            filter = QualityFilter.HD
            sort = SortOrder.QUALITY_THEN_SIZE

        # first try to find a cached candidate with the full season
        streams = await tc.get_show_streams(
            request.imdb_id, request.season_id, 1, filter=filter, sort_order=sort
        )

        rdd = RealDebridDownloader(rdbc, request=request, streams=streams)
        downloaded = await rdd.download_show(await rdd.instantly_available_streams)
        if downloaded:
            sync.refresh.set()
            return

        logger.info("Unable to find any matching torrents")

    if backoff_to_episodes:
        logger.info("Searching for individual episodes")
        for er in request.to_episode_requests():
            with structlog.contextvars.bound_contextvars(**er.ctx):
                await handle_episode_request(er, tc, rdbc, sync, cache)


async def handle_episode_request(
    request: EpisodeRequest,
    tc: TorrentioClient,
    rdbc: RealDebridClient,
    sync: Synchronizer,
    cache: Cache,
):
    cache_key = f"{request.imdb_id}:{request.season_id}:{request.episode_id}"
    if cache_key in cache:
        logger.debug("Ignoring cached request")
        return

    async with sync.semaphore:
        logger.info("Starting request handler")

        if tc.is_older_media(request.release_year):
            filter = QualityFilter.OLD
            sort = SortOrder.SEEDERS
        else:
            filter = QualityFilter.HD
            sort = SortOrder.QUALITY_THEN_SIZE

        streams = await tc.get_show_streams(
            request.imdb_id,
            request.season_id,
            request.episode_id,
            filter=filter,
            sort_order=sort,
        )

        # search for a cached torrent with just the episode we want
        rdd = RealDebridDownloader(rdbc, request=request, streams=streams)
        downloaded = await rdd.download_episode(await rdd.instantly_available_streams)
        if downloaded:
            sync.refresh.set()
            return

        # search for the episode we want inside of a cached torrent
        downloaded = await rdd.download_episode_from_bundle(
            await rdd.instantly_available_streams
        )
        if downloaded:
            sync.refresh.set()
            cache[cache_key] = True
            return

        # search for an uncached torrent with just the episode we want
        # TODO: sort the streams ourselves
        downloaded = await rdd.download_episode(await rdd.unavailable_streams)
        if downloaded:
            sync.refresh.set()
            cache[cache_key] = True
            return

        logger.info("Unable to find any matching torrents")


async def runit(run_once: bool = True, tmdb_id: int | None = None):
    cfg = Config()
    setup_logging(cfg.jellbrid_log_level)
    if cfg.dev_mode:
        logger.warning("Running in dev-mode. Nothing will be downloaded")

    # make these here to persist caches across runs
    rdbc = RealDebridClient(cfg)
    tc = TorrentioClient(cfg)
    cache = cachetools.TTLCache(100, 60 * 60)

    while True:
        await handler(cfg, rdbc=rdbc, tc=tc, cache=cache, tmdb_id=tmdb_id)
        logger.info("Completed request processing")
        if run_once:
            break
        await anyio.sleep(60)


def main():
    anyio.run(runit)


if __name__ == "__main__":
    anyio.run(runit)
