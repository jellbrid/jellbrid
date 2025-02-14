from rich.pretty import pprint

from jellbrid.cli.base import AsyncTyper
from jellbrid.clients.seers import SeerrsClient, parse_request
from jellbrid.config import Config

app = AsyncTyper()


@app.command()
async def sync():
    seerrs = SeerrsClient(Config())
    await seerrs.sync_with_jellyfin()


@app.command()
async def show_requests():
    from jellbrid.clients.jellyfin import JellyfinClient

    cfg = Config()
    sc = SeerrsClient(cfg)
    jc = JellyfinClient(cfg)

    reqs = []
    for request in await sc.get_processing_requests():
        for req in await parse_request(sc, jc, request, ignore_partials=False):
            reqs.append(req)
    pprint(reqs)


@app.command()
async def get_request(req: int):
    seerrs = SeerrsClient(Config())
    request = await seerrs.get_request(req)
    pprint(request)


@app.command()
async def get_details(tmdb_id: int):
    from jellbrid.clients.jellyfin import JellyfinClient

    cfg = Config()
    seerrs = SeerrsClient(cfg)
    request = await seerrs.get_show_details(tmdb_id)
    jf_media_id = request["mediaInfo"]["jellyfinMediaId"]

    jfc = JellyfinClient(cfg)
    episodes = await jfc.get_episodes_in_season(jf_media_id)
    pprint({e["Name"] for e in episodes}, indent_guides=False)
