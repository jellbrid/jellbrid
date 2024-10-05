import typing as t


class RequestedSeason(t.TypedDict):
    id: int
    seasonNumber: int


class PageInfo(t.TypedDict):
    pages: int
    pageSize: int
    results: int
    page: int


class SeerrMediaRequest(t.TypedDict):
    id: int
    status: int
    type: str
    is4k: bool
    seasons: list[RequestedSeason]
    updatedAt: str
    createdAt: str
    media: dict


class SeerrMediaInfo(t.TypedDict):
    id: int
    tmdbId: int
    tvdbId: int | None
    imdbId: int | None
    status: int
    createdAt: str
    updatedAt: str
    seasons: list["MediaRequestSeason"]
    jellyfinMediaId: str


class MediaRequestSeason(t.TypedDict):
    id: int
    seasonNumber: int
    status: int


class SeerrMovieDetail(t.TypedDict):
    imdbId: str
    title: str
    releaseDate: str


class ExternalIds(t.TypedDict):
    imdbId: str


class SeerrShowDetail(t.TypedDict):
    externalIds: ExternalIds
    name: str
    seasons: list["ShowDetailSeason"]
    mediaInfo: "SeerrMediaInfo"


class ShowDetailSeason(t.TypedDict):
    episodeCount: int
    seasonNumber: int
    id: int
