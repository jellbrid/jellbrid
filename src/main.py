import typing as t

import anyio
import cachetools
import structlog
from cachetools import Cache

from jellbrid.clients.jellyfin import JellyfinClient, scan_and_wait_for_completion
from jellbrid.clients.realdebrid import RealDebridClient, download
from jellbrid.clients.realdebrid.filters import (
    has_file_count,
    has_file_ratio,
    is_cached_torrent,
)
from jellbrid.clients.seers import SeerrsClient, get_requests
from jellbrid.clients.torrentio import SortOrder, TorrentioClient
from jellbrid.clients.torrentio.filters import name_contains_full_season
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
    cfg: Config, *, rdbc: RealDebridClient, tc: TorrentioClient, cache: Cache
):
    seers = SeerrsClient(cfg)
    jc = JellyfinClient(cfg)
    sync = Synchronizer(cfg)

    async with anyio.create_task_group() as tg:
        async for request in get_requests(seers, jc):
            with structlog.contextvars.bound_contextvars(
                **request.ctx, dev_mode=cfg.dev_mode
            ):
                if request.tmdb_id != 533535:
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
        streams = await tc.get_movie_streams(request.imdb_id)

        for s in streams:
            if await is_cached_torrent(rdbc, s) and await has_file_count(rdbc, s, 1):
                if await download(rdbc, s):
                    sync.refresh.set()
                    return

        streams = await tc.get_movie_streams(
            request.imdb_id,
            sort_order=SortOrder.QUALITY_THEN_SEEDERS,
        )
        for s in streams[:5]:
            if await has_file_count(rdbc, s, 1):
                await download(rdbc, s)
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
        streams = await tc.get_show_streams(request.imdb_id, request.season_id, 1)

        # first try to find a cached candidate with the full season
        for s in streams:
            if (
                name_contains_full_season(tc, s, request)
                and await is_cached_torrent(rdbc, s)
                and await has_file_ratio(rdbc, s, request, 0.8)
            ):
                if await download(rdbc, s):
                    sync.refresh.set()
                    return

        # then try to find a cached candidate that hopefully has most of the
        # files we want. we can download the episodes individually later on
        for s in streams:
            if name_contains_full_season(tc, s, request) and await is_cached_torrent(
                rdbc, s
            ):
                if await download(rdbc, s):
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
        streams = await tc.get_show_streams(
            request.imdb_id, request.season_id, request.episode_id
        )

        # search for a cached torrent with just the episode we want
        for s in streams:
            if await is_cached_torrent(rdbc, s) and await has_file_count(rdbc, s, 1):
                if await download(rdbc, s):
                    sync.refresh.set()
                    return

        streams = await tc.get_show_streams(
            request.imdb_id,
            request.season_id,
            request.episode_id,
            sort_order=SortOrder.QUALITY_THEN_SEEDERS,
        )

        # search for an uncached torrent with just the episode we want
        for s in streams[:5]:
            if await has_file_count(rdbc, s, 1):
                if await download(rdbc, s):
                    cache[cache_key] = True
                    return

        logger.info("Unable to find any matching torrents")


async def runit(run_once: bool = True):
    cfg = Config()
    setup_logging(cfg.jellbrid_log_level)
    if cfg.dev_mode:
        logger.warning("Running in dev-mode. Nothing will be downloaded")

    # make these here to persist caches across runs
    rdbc = RealDebridClient(cfg)
    tc = TorrentioClient(cfg)
    cache = cachetools.TTLCache(100, 60 * 60)

    while True:
        await handler(cfg, rdbc=rdbc, tc=tc, cache=cache)
        logger.info("Completed request processing")
        if run_once:
            break
        await anyio.sleep(60)


def main():
    anyio.run(runit)


if __name__ == "__main__":
    anyio.run(runit)
