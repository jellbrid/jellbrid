from rich.pretty import pprint

from jellbrid.cli.base import AsyncTyper
from jellbrid.clients.torrentio import TorrentioClient
from jellbrid.config import Config

app = AsyncTyper()


@app.command()
async def lookup_show(show_id: str, season: int, episode: int):
    tc = TorrentioClient(Config())

    results = await tc.get_show_streams(show_id, season, episode)
    pprint(results)


@app.command()
async def lookup_movie(movie_id: str):
    tc = TorrentioClient(Config())

    results = await tc.get_movie_streams(movie_id)
    pprint(results)
