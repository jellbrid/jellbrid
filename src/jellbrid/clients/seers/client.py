import typing as t
import urllib.parse

from jellbrid.clients.base import BaseClient
from jellbrid.clients.seers.types import (
    SeerrMediaRequest,
    SeerrMovieDetail,
    SeerrShowDetail,
)
from jellbrid.config import Config


class SeerrsClient:
    def __init__(self, cfg: Config):
        url = cfg.seerr_url
        self.api_path = "api/v1/"
        api_url = urllib.parse.urljoin(url, self.api_path)
        self.client = BaseClient(api_url, headers={"X-Api-Key": cfg.seerr_api_key})
        self.cfg = cfg

    async def get_processing_requests(self) -> list[SeerrMediaRequest]:
        params = {"take": 1000, "skip": 0, "filter": "processing"}
        response = await self.client.request("GET", "request/", params=params)
        return t.cast(list[SeerrMediaRequest], response["results"])

    async def get_movie_details(self, movie_id: int) -> SeerrMovieDetail:
        response = await self.client.request("GET", f"movie/{movie_id}/")
        return t.cast(SeerrMovieDetail, response)

    async def get_show_details(self, show_id: int) -> SeerrShowDetail:
        response = await self.client.request("GET", f"tv/{show_id}/")
        return t.cast(SeerrShowDetail, response)

    async def sync_with_jellyfin(self):
        return await self.client.request("POST", "settings/jobs/jellyfin-full-scan/run")

    async def get_request(self, id: int):
        return await self.client.request("GET", f"request/{id}")

    async def get_episodes_in_season(self, tmdb_id: int, season_id: int) -> list[dict]:
        result = await self.client.request("GET", f"tv/{tmdb_id}/season/{season_id}")
        return result["episodes"]
