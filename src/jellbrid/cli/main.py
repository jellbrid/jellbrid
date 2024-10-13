import typing as t

import typer

from jellbrid.cli.base import AsyncTyper
from jellbrid.cli.jellyfin import app as jellfin
from jellbrid.cli.realdebrid import app as realdebrid
from jellbrid.cli.seers import app as seerrs
from jellbrid.cli.torrentio import app as torrentio
from main import runit

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
    print("Running jellbrid CLI command")
    await runit(run_once=not loop, tmdb_id=tmdb_id)
