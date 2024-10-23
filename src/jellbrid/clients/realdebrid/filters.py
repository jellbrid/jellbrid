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


def movie_name_filter(filename: str, name: str) -> bool:
    for word in name.lower().split():
        word = word.strip(":")
        if word not in filename.lower():
            return False

    return True


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
