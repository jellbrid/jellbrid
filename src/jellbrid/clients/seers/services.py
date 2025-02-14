import typing as t

import structlog

from jellbrid.clients.jellyfin import JellyfinClient
from jellbrid.clients.seers.client import SeerrsClient
from jellbrid.clients.seers.types import SeerrMediaRequest, SeerrShowDetail
from jellbrid.requests import EpisodeRequest, MediaRequest, MovieRequest, SeasonRequest

logger = structlog.get_logger(__name__)


async def parse_request(
    sc: SeerrsClient,
    jc: JellyfinClient,
    request: SeerrMediaRequest,
    *,
    ignore_partials: bool = True,
):
    tmdb_id = request["media"]["tmdbId"]

    if request["type"] == "movie":
        details = await sc.get_movie_details(tmdb_id)
        mr = MovieRequest(
            title=details["title"],
            imdb_id=details["imdbId"],
            tmdb_id=tmdb_id,
            release_date=details["releaseDate"],
            alt_title=details["originalTitle"],
        )
        return [t.cast(MediaRequest, mr)]

    details = await sc.get_show_details(tmdb_id)
    full_request = await sc.get_request(request["id"])

    results: list[MediaRequest] = []
    # process seasons that we already have some media for
    processed_seasons = set()
    for season in full_request["media"]["seasons"]:
        season_id = season["seasonNumber"]
        processed_seasons.add(season_id)
        if season["status"] == 5:
            # This season is already available
            continue
        elif season["status"] == 4:
            # This season is partially available
            if ignore_partials:
                continue

            ers = await create_episode_requests(
                sc, jc, request=request, season_id=season_id, show_info=details
            )
            results.extend(t.cast(list[MediaRequest], ers))

        elif season["status"] == 2:
            logger.error("How did we get here? We should never get here")
            season_id = season_id
            episodes = await sc.get_episodes_in_season(tmdb_id, season_id)
            sr = SeasonRequest(
                title=details["name"],
                tmdb_id=tmdb_id,
                imdb_id=details["externalIds"]["imdbId"],
                season_id=season_id,
                episodes=[e["name"] for e in episodes],
                release_date=details["firstAirDate"],
            )
            results.append(t.cast(MediaRequest, sr))
        elif season["status"] == 1:
            # status is unknown
            processed_seasons.discard(season_id)

    # process all requested seasons, ignoring the ones we processed above
    for season in full_request["seasons"]:
        season_id = season["seasonNumber"]
        if season_id in processed_seasons:
            continue

        processed_seasons.add(season_id)
        episodes = await sc.get_episodes_in_season(tmdb_id, season_id)
        sr = SeasonRequest(
            title=details["name"],
            alt_title=details["originalName"],
            tmdb_id=tmdb_id,
            imdb_id=details["externalIds"]["imdbId"],
            season_id=season_id,
            episodes=[e["name"] for e in episodes],
            release_date=details["firstAirDate"],
        )
        results.append(t.cast(MediaRequest, sr))
    return results


async def create_episode_requests(
    sc: SeerrsClient,
    jc: JellyfinClient,
    *,
    request: SeerrMediaRequest,
    season_id: int,
    show_info: SeerrShowDetail,
):
    tmdb_id = request["media"]["tmdbId"]
    all_episodes_in_season = await sc.get_episodes_in_season(tmdb_id, season_id)
    season_names_to_episodes = {e["name"]: e for e in all_episodes_in_season}

    # get the JF Season-IDs for the seasons that we have
    jf_media_id = request["media"]["jellyfinMediaId"]
    all_episodes_in_jf = await jc.get_episodes_in_season(jf_media_id, season_id)
    jf_episode_names = {e["Name"] for e in all_episodes_in_jf}

    for episode in jf_episode_names:
        season_names_to_episodes.pop(episode, None)

    results: list[EpisodeRequest] = []
    for episode in season_names_to_episodes.values():
        er = EpisodeRequest(
            title=show_info["name"],
            alt_title=show_info["originalName"],
            episode_name=episode["name"],
            tmdb_id=tmdb_id,
            imdb_id=show_info["externalIds"]["imdbId"],
            season_id=season_id,
            episode_id=episode["episodeNumber"],
            release_date=episode["airDate"],
        )
        results.append(er)
    return results


async def get_requests(
    sc: SeerrsClient, jc: JellyfinClient
) -> t.AsyncIterator[MediaRequest]:
    for request in await sc.get_processing_requests():
        for req in await parse_request(sc, jc, request, ignore_partials=False):
            yield req
