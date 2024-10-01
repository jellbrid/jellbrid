from jellbrid.clients.realdebrid import RealDebridClient
from jellbrid.clients.torrentio import Stream
from jellbrid.requests import SeasonRequest


async def is_cached_torrent(rdbc: RealDebridClient, s: Stream) -> bool:
    return await rdbc.has_cached(s["infoHash"])


async def has_file_count(rdbc: RealDebridClient, s: Stream, count: int):
    if await rdbc.has_cached(s["infoHash"]):
        files = await rdbc.collect_file_ids_from_cached_torrent(s["infoHash"])
    else:
        files = await rdbc.collect_file_ids_from_uncached_torrent(s["infoHash"])

    return len(files) == count


async def has_file_ratio(
    rdbc: RealDebridClient, s: Stream, request: SeasonRequest, ratio: float
):
    if await rdbc.has_cached(s["infoHash"]):
        files = await rdbc.collect_file_ids_from_cached_torrent(s["infoHash"])
    else:
        files = await rdbc.collect_file_ids_from_uncached_torrent(s["infoHash"])

    return (len(files) / len(request.episodes)) > ratio
