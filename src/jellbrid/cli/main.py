from jellbrid.cli.base import AsyncTyper
from jellbrid.cli.jellyfin import app as jellfin
from jellbrid.cli.realdebrid import app as realdebrid
from jellbrid.cli.seers import app as seerrs
from jellbrid.cli.torrentio import app as torrentio

app = AsyncTyper()


app.add_typer(realdebrid, name="rd")
app.add_typer(torrentio, name="torrentio")
app.add_typer(jellfin, name="jf")
app.add_typer(seerrs, name="seerrs")
