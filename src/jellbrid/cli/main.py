import typing as t

import anyio
import anyio.from_thread
import anyio.to_thread
import typer
from hypercorn.asyncio import serve

from jellbrid.cli.base import AsyncTyper
from jellbrid.cli.jellyfin import app as jellfin
from jellbrid.cli.realdebrid import app as realdebrid
from jellbrid.cli.seers import app as seerrs
from jellbrid.cli.torrentio import app as torrentio
from server import app as server_app
from server import get_server_config

app = AsyncTyper()


app.add_typer(realdebrid, name="rd")
app.add_typer(torrentio, name="torrentio")
app.add_typer(jellfin, name="jf")
app.add_typer(seerrs, name="seerrs")


@app.command()
async def jellbrid(
    loop: t.Annotated[bool, typer.Option("--loop")] = False,
    tmdb_id: int | None = None,
):
    async with anyio.create_task_group() as tg:
        # tg.start_soon(runit, not loop, tmdb_id)
        tg.start_soon(serve, server_app, get_server_config())
