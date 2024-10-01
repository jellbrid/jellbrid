import structlog
from structlog.contextvars import bound_contextvars

from jellbrid.clients.realdebrid.client import RealDebridClient
from jellbrid.clients.torrentio import Stream

logger = structlog.get_logger(__name__)


async def download(rdbc: RealDebridClient, stream: Stream):
    is_cached = await rdbc.has_cached(stream["infoHash"])

    with bound_contextvars(hash=stream["infoHash"], cached=is_cached):
        if rdbc.cfg.dev_mode:
            logger.info("Skipped downloading torrent")
            return True

        torrent = await rdbc.add_magnet(stream["infoHash"])
        torrent_id = torrent.get("id")
        if torrent_id is None:
            logger.warning("Unable to add magnet", **torrent)
            return False

        if is_cached:
            files = await rdbc.collect_file_ids_from_cached_torrent(stream["infoHash"])
        else:
            files = await rdbc.collect_file_ids_from_new_torrent(torrent["id"])

        result = await rdbc.select_files(torrent["id"], files)
        if "error" in result:
            logger.warning("Unable to start torrent", **result)
            result = await rdbc.delete_magnet(torrent_id)
            return False

        logger.info("Downloaded torrent")
        return True
