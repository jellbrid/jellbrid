import typing as t


class CachedTorrent(t.TypedDict):
    filename: str
    filesize: int


class MagnetAddedResponse(t.TypedDict):
    uri: str
    id: str
