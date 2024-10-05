from jellbrid.clients.torrentio.client import TorrentioClient
from jellbrid.clients.torrentio.types import Stream
from jellbrid.requests import SeasonRequest
from jellbrid.requests.main import MovieRequest


def name_contains_full_season(s: Stream, request: SeasonRequest) -> bool:
    return TorrentioClient.contains_full_season_filter(s, request.season_id)


def name_contains_release_year(s: Stream, request: MovieRequest) -> bool:
    return request.release_year in s["title"]
