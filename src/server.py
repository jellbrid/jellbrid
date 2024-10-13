import logging

from hypercorn.config import Config as HypercornConfig
from quart import Quart

from jellbrid.config import Config
from main import runit

app = Quart(__name__)


@app.post("/")
async def new_request_received():
    app.add_background_task(runit, run_once=True)
    return {"result": "ok"}


def get_server_config():
    cfg = Config()
    hcfg = HypercornConfig()
    hcfg.bind = [f"0.0.0.0:{cfg.server_port}"]
    hcfg.loglevel = logging.getLevelName(cfg.jellbrid_log_level)
    return hcfg
