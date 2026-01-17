import datetime
import enum
import re

from async_lru import alru_cache

from jellbrid.clients.base import BaseClient
from jellbrid.clients.torrentio.types import Stream
from jellbrid.config import Config


class SortOrder(enum.Enum):
    QUALITY_THEN_SIZE = "qualitysize"
    QUALITY_THEN_SEEDERS = ""
    SEEDERS = "seeders"


class QualityFilter(enum.Enum):
    UHD = "480p,scr,cam,720p,1080p"
    HD = "480p,scr,cam,720p"
    OLD = "scr,cam"


class TorrentioClient:
    def __init__(self, cfg: Config):
        self.client = BaseClient(cfg.torrentio_url, {"User-Agent": "HTTPie/3.2.2"})
        self.cfg = cfg
        self.rd_api_key = cfg.rd_api_key

    def is_older_media(self, release_year: str):
        release_year_ = int(release_year)
        return (datetime.datetime.now().year - release_year_) > 40

    def path_for_options(self, order: SortOrder, filter: QualityFilter) -> str:
        # path = f"sort={order.value}|qualityfilter={filter.value}|debridoptions=nodownloadlinks,nocatalog|realdebrid={self.rd_api_key}/stream"
        path = f"sort={order.value}|qualityfilter={filter.value}/stream"
        return path

    @alru_cache(ttl=60 * 60)  # cache torrents for 60 minutes
    async def get_movie_streams(
        self,
        movie_id: str,
        *,
        sort_order: SortOrder = SortOrder.QUALITY_THEN_SIZE,
        filter: QualityFilter = QualityFilter.HD,
    ) -> list[Stream]:
        path = self.path_for_options(sort_order, filter)
        path = f"{path}/movie/{movie_id}.json"
        response = await self.client.request("GET", path)
        return response["streams"]

    @alru_cache(ttl=60 * 60)  # cache torrents for 60 minutes
    async def get_show_streams(
        self,
        show_id: str,
        season: int,
        episode: int,
        *,
        sort_order: SortOrder = SortOrder.QUALITY_THEN_SIZE,
        filter: QualityFilter = QualityFilter.HD,
    ) -> list[Stream]:
        season_ = f"{season}".zfill(2)
        episode_ = f"{episode}".zfill(2)
        path = self.path_for_options(sort_order, filter)
        path = f"{path}/series/{show_id}:{season_}:{episode_}.json"
        response = await self.client.request("GET", path)
        return response["streams"]

    @staticmethod
    def contains_full_season_filter(s: Stream, season: int) -> bool:
        season_ = f"{season}".zfill(2)

        for pattern in [
            rf".S{season_}\.",  # abc.S01.xyz
            rf"\[S{season_}\]",  # [S01]
            rf"\sS{season_}\s",  # abc S01 abc
        ]:
            if re.search(pattern, s["title"], re.IGNORECASE):
                return True
        return False
