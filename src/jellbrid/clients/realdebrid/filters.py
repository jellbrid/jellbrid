from jellbrid.clients.realdebrid import RealDebridClient
from jellbrid.clients.torrentio import Stream


async def has_file_count(rdbc: RealDebridClient, s: Stream, count: int):
    bundle = await rdbc.get_rd_bundle_with_file_count(s["infoHash"], count)
    return True if bundle else False


def episode_filter(name: str, season_id: int, episode_id: int):
    """This function can be used to filter RD bundles for cached torrents"""

    name = name.lower()
    if f"s{season_id}e{episode_id}" in name:
        return True
    if f"s{season_id}.e{episode_id}" in name:
        return True

    season_ = f"{season_id}".zfill(2)
    episode_ = f"{episode_id}".zfill(2)
    if f"s{season_}e{episode_}" in name:
        return True
    if f"s{season_}.e{episode_}" in name:
        return True
    return False


def filter_samples(filename: str):
    """This function can be used to filter RD bundles for cached torrents"""
    return "sample" not in filename.lower()


def filter_extension(filename: str):
    """This function can be used to filter RD bundles for cached torrents"""

    filename = filename.lower()
    return (
        filename.endswith("mp4")
        or filename.endswith("mkv")
        or filename.endswith("avi")
        or filename.endswith("mpg")
    )
