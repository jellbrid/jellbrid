from cachetools import Cache

from jellbrid.requests.main import EpisodeRequest, MovieRequest, SeasonRequest


class RequestCache:
    """
    A cache for ensuring that requests are not infinitely processed if the media
    library is unable to accurately identify the media
    """

    def __init__(self, mazsize: int = 100) -> None:
        self.cache = Cache(maxsize=mazsize)

    def _key_for_request(
        self, request: MovieRequest | SeasonRequest | EpisodeRequest
    ) -> str:
        match request:
            case MovieRequest():
                key = request.imdb_id
            case SeasonRequest():
                key = f"{request.imdb_id}-{request.season_id}"
            case EpisodeRequest():
                key = f"{request.imdb_id}-{request.season_id}-{request.episode_id}"
        return key

    def has_request(self, request: MovieRequest | SeasonRequest | EpisodeRequest):
        key = self._key_for_request(request)
        return key in self.cache

    def add_request(self, request: MovieRequest | SeasonRequest | EpisodeRequest):
        key = self._key_for_request(request)
        self.cache[key] = request
