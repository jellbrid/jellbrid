from jellbrid.clients.torrentio.client import TorrentioClient
from jellbrid.clients.torrentio.types import Stream
from jellbrid.requests import SeasonRequest


def name_contains_full_season(
    tc: TorrentioClient, s: Stream, request: SeasonRequest
) -> bool:
    return tc.contains_full_season_filter(s, request.season_id)
