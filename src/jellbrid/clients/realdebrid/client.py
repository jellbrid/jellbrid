import typing as t
from contextlib import asynccontextmanager

import structlog
from async_lru import alru_cache
from cachetools import TTLCache

from jellbrid.clients.base import BaseClient
from jellbrid.clients.realdebrid.bundle import RDBundleManager
from jellbrid.clients.realdebrid.types import (
    InstantAvailablityType,
    MagnetAddedResponse,
    RDBundleFileFilter,
    TorrentStatus,
)
from jellbrid.config import Config

logger = structlog.get_logger(__name__)


class RealDebridClient:
    def __init__(self, cfg: Config):
        self.client = BaseClient(
            url=cfg.rd_api_url, headers={"Authorization": f"Bearer {cfg.rd_api_key}"}
        )
        self.cfg = cfg
        self.cache = TTLCache(maxsize=200, ttl=60 * 60)

    async def get_instant_availability_data(
        self, hashes: list[str]
    ) -> InstantAvailablityType:
        """
        Returns results for some/all hashes from a cache, if possible
        """
        results, misses = {}, []

        # get results from cache
        for h in [h.lower() for h in hashes]:
            cached_data = self.cache.get(h, None)
            if cached_data is not None:
                results[h] = cached_data
            else:
                misses.append(h)

        if misses:
            # submit a request for missing hashes
            all_data = await self._get_instant_availability_data(misses)

            # update cache with results from data
            for key, data in all_data.items():
                self.cache[key] = data

            # update our results
            results.update(all_data)

        return results

    async def _get_instant_availability_data(
        self, hashes: list[str]
    ) -> InstantAvailablityType:
        """
        Performs the base HTTP request against RD, with some normalization if needed
        """
        hashes_ = [h.lower() for h in hashes]
        result = await self.client.request(
            "GET", f"torrents/instantAvailability/{'/'.join(hashes_)}"
        )
        if isinstance(result, list):
            result = {}

        return result

    async def filter_instantly_available(
        self, hashes: list[str]
    ) -> InstantAvailablityType:
        candidates = await self.get_instant_availability_data(hashes)

        results = {}
        for key, data in candidates.items():
            if data == []:
                continue
            if data.get("rd", []) == []:
                continue
            results[key] = data
        return results

    async def instantly_available(self, hash: str) -> bool:
        result = await self.get_instant_availability_data([hash])
        if result.get(hash, {}) == []:
            return False
        rd_data = result.get(hash, {}).get("rd", [])
        return len(rd_data) > 0

    async def add_magnet(self, hash: str) -> MagnetAddedResponse:
        if not hash.startswith("magnet:?xt=urn:btih:"):
            magnet = f"magnet:?xt=urn:btih:{hash}"

        result = await self.client.request(
            "POST", "torrents/addMagnet", data={"magnet": magnet}
        )
        return t.cast(MagnetAddedResponse, result)

    async def delete_magnet(self, id: str):
        return await self.client.request("DELETE", f"torrents/delete/{id}")

    async def select_files(self, torrent_id: str, files: t.Iterable[str]) -> dict:
        files = [str(f) for f in files]
        return await self.client.request(
            "POST",
            f"torrents/selectFiles/{torrent_id}",
            data={"files": ",".join(files)},
        )

    async def get_torrents(self, status: TorrentStatus | None = None):
        results = await self.client.request("GET", "torrents")
        if status:
            return [r for r in results if r["status"] == status.value]
        return results

    async def get_torrent_files_info(self, torrent_id: str) -> dict:
        return await self.client.request("GET", f"torrents/info/{torrent_id}")

    @alru_cache(ttl=60 * 60)
    async def collect_data_from_uncached_torrent(self, hash: str) -> dict:
        async with self.tmp_torrent(hash) as tmp_torrent_id:
            data = await self.get_torrent_files_info(tmp_torrent_id)
        return data

    @asynccontextmanager
    async def tmp_torrent(self, hash: str):
        torrent = await self.add_magnet(hash)
        torrent_id = torrent.get("id")
        if torrent_id is None:
            logger.warning("Unable to add magnet", **torrent)
            return
        try:
            yield torrent_id
        finally:
            await self.delete_magnet(torrent_id)

    async def get_rd_bundle_with_file_count(
        self,
        hash: str,
        count: int,
        *,
        file_filters: list[RDBundleFileFilter] | None = None,
    ):
        rdc = await self._get_bundle_manager(hash, file_filters)
        return rdc.get_bundle_of_size(count)

    async def get_rd_bundle_with_file_count_gte(
        self,
        hash: str,
        count: int,
        *,
        file_filters: list[RDBundleFileFilter] | None = None,
    ):
        rdc = await self._get_bundle_manager(hash, file_filters)
        return rdc.get_bundle_gte_size(count)

    async def get_rd_bundle_with_file_match(
        self, hash: str, *, file_filters: list[RDBundleFileFilter] | None = None
    ):
        rdc = await self._get_bundle_manager(hash, file_filters)
        return rdc.get_bundle_with_match()

    async def _get_bundle_manager(
        self, hash: str, file_filters: list[RDBundleFileFilter] | None = None
    ):
        data = await self.collect_data_from_uncached_torrent(hash)
        return RDBundleManager(data, file_filters=file_filters)
