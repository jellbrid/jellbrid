import typing as t
from contextlib import asynccontextmanager

import structlog
from async_lru import alru_cache

from jellbrid.clients.base import BaseClient
from jellbrid.clients.realdebrid.types import MagnetAddedResponse, TorrentStatus
from jellbrid.config import Config

logger = structlog.get_logger(__name__)


class RealDebridClient:
    def __init__(self, cfg: Config):
        self.client = BaseClient(
            url=cfg.rd_api_url, headers={"Authorization": f"Bearer {cfg.rd_api_key}"}
        )
        self.cfg = cfg

    @alru_cache(ttl=60 * 60)
    async def get_cached_torrent_data(
        self, hash: str
    ) -> dict[str, list[dict[str, dict]]]:
        hash = hash.lower()
        result = await self.client.request(
            "GET", f"torrents/instantAvailability/{hash}"
        )
        if isinstance(result, list):
            result = {}

        data = result.get(hash, {})
        return {} if data == [] else data

    async def has_cached(self, hash: str) -> bool:
        result = await self.get_cached_torrent_data(hash)
        rd_data = result.get("rd", [])
        return len(rd_data) > 0

    async def get_torrent_files_info(self, torrent_id: str) -> dict:
        return await self.client.request("GET", f"torrents/info/{torrent_id}")

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
        return await self.client.request(
            "POST",
            f"torrents/selectFiles/{torrent_id}",
            data={"files": ",".join(files)},
        )

    async def collect_file_ids_from_new_torrent(self, torrent_id: str) -> set[str]:
        info = await self.get_torrent_files_info(torrent_id)

        files_to_get: set[str] = set()
        for file_data in info.get("files", []):
            filename: str = file_data.get("path").lower()
            file_id = file_data.get("id")
            if "sample" in filename:
                continue
            if (
                filename.endswith("mp4")
                or filename.endswith("mkv")
                or filename.endswith("avi")
            ):
                files_to_get.add(str(file_id))
        return files_to_get

    async def collect_file_ids_from_cached_torrent(self, hash: str) -> set[str]:
        return await self._collect_files_from_cached_torrent(hash, "file_id")

    async def collect_filenames_from_cached_torrent(self, hash: str) -> set[str]:
        return await self._collect_files_from_cached_torrent(hash, "filename")

    async def _collect_files_from_cached_torrent(
        self, hash: str, item: t.Literal["filename"] | t.Literal["file_id"]
    ) -> set[str]:
        cached_response = await self.get_cached_torrent_data(hash)

        files_to_get: set[str] = set()
        for file_entry in cached_response.get("rd", []):
            for file_id, file_data in file_entry.items():
                filename: str = file_data.get("filename", "").lower()
                if "sample" in filename:
                    continue
                if (
                    filename.endswith("mp4")
                    or filename.endswith("mkv")
                    or filename.endswith("avi")
                ):
                    if item == "filename":
                        files_to_get.add(filename)
                    if item == "file_id":
                        files_to_get.add(file_id)
        return files_to_get

    @alru_cache(ttl=60 * 60)
    async def collect_file_ids_from_uncached_torrent(self, hash: str) -> set[str]:
        async with self.tmp_torrent(hash) as tmp_torrent_id:
            files = await self.collect_file_ids_from_new_torrent(tmp_torrent_id)
        return files

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

    async def get_torrents(self, status: TorrentStatus | None = None):
        results = await self.client.request("GET", "torrents")
        if status:
            return [r for r in results if r["status"] == status.value]
        return results
