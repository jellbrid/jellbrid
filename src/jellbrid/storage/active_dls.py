import datetime
from dataclasses import dataclass, field

from jellbrid.requests import EpisodeRequest, MovieRequest, SeasonRequest


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


@dataclass
class ActiveDownload:
    imdb_id: str
    tmdb_id: int
    title: str
    torrent_id: str
    created_at: datetime.datetime = field(default_factory=_utc_now)
    episode: int | None = None
    season: int | None = None

    @classmethod
    def from_movie_request(cls, request: MovieRequest, torrent_id: str):
        return cls(
            imdb_id=request.imdb_id,
            tmdb_id=request.tmdb_id,
            title=request.title,
            torrent_id=torrent_id,
        )

    @classmethod
    def from_season_request(cls, request: SeasonRequest, torrent_id: str):
        return cls(
            imdb_id=request.imdb_id,
            tmdb_id=request.tmdb_id,
            title=request.title,
            torrent_id=torrent_id,
            season=request.season_id,
        )

    @classmethod
    def from_episode_request(cls, request: EpisodeRequest, torrent_id: str):
        return cls(
            imdb_id=request.imdb_id,
            tmdb_id=request.tmdb_id,
            title=request.title,
            torrent_id=torrent_id,
            season=request.season_id,
            episode=request.episode_id,
        )
