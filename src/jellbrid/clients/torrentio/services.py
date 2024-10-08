from jellbrid.clients.torrentio.client import QualityFilter, SortOrder, TorrentioClient
from jellbrid.requests import EpisodeRequest, MovieRequest, SeasonRequest


async def get_streams_for_movie(tc: TorrentioClient, request: MovieRequest):
    if tc.is_older_media(request.release_year):
        filter = QualityFilter.OLD
        sort = SortOrder.SEEDERS
    else:
        filter = QualityFilter.HD
        sort = SortOrder.QUALITY_THEN_SIZE

    return await tc.get_movie_streams(request.imdb_id, filter=filter, sort_order=sort)


async def get_streams_for_show(
    tc: TorrentioClient, request: SeasonRequest | EpisodeRequest
):
    if tc.is_older_media(request.release_year):
        filter = QualityFilter.OLD
        sort = SortOrder.SEEDERS
    else:
        filter = QualityFilter.HD
        sort = SortOrder.QUALITY_THEN_SIZE

    episode = 1 if isinstance(request, SeasonRequest) else request.episode_id
    return await tc.get_show_streams(
        request.imdb_id,
        season=request.season_id,
        episode=episode,
        filter=filter,
        sort_order=sort,
    )
