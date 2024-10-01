import enum
from dataclasses import asdict, dataclass


class MediaType(enum.Enum):
    Movie = enum.auto()
    Season = enum.auto()
    Episode = enum.auto()

    def __repr__(self):
        return self._name_


@dataclass(kw_only=True)
class MediaRequest:
    type: MediaType
    imdb_id: str
    tmdb_id: int
    title: str

    @property
    def ctx(self) -> dict:
        return asdict(self)


@dataclass(kw_only=True)
class MovieRequest(MediaRequest):
    type: MediaType = MediaType.Movie


@dataclass(kw_only=True)
class SeasonRequest(MediaRequest):
    type: MediaType = MediaType.Season
    season_id: int
    episodes: list[str]

    @property
    def ctx(self) -> dict:
        s = asdict(self)
        s["episodes"] = len(self.episodes)
        return s

    def to_episode_requests(self) -> list["EpisodeRequest"]:
        requests = []
        for i, name in enumerate(self.episodes, start=1):
            er = EpisodeRequest(
                imdb_id=self.imdb_id,
                tmdb_id=self.tmdb_id,
                title=self.title,
                season_id=self.season_id,
                episode_name=name,
                episode_id=i,
            )
            requests.append(er)
        return requests


@dataclass(kw_only=True)
class EpisodeRequest(MediaRequest):
    type: MediaType = MediaType.Episode
    episode_name: str
    season_id: int
    episode_id: int
