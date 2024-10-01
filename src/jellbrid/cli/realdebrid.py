import anyio
import httpx
from authlib.integrations import httpx_client
from rich.pretty import pprint

from jellbrid.cli.base import AsyncTyper
from jellbrid.clients.realdebrid import RealDebridClient
from jellbrid.config import Config

app = AsyncTyper()


@app.command()
async def lookup_hash(hash: str):
    rdbc = RealDebridClient(Config())

    results = await rdbc.get_cached_torrent_data(hash)
    pprint(results)


@app.command()
async def instant_availability(hash: str):
    rdbc = RealDebridClient(Config())
    result = await rdbc.has_cached(hash)
    pprint(result)


@app.command()
async def show_files(hash: str):
    rdbc = RealDebridClient(Config())
    files_in_stream = await rdbc.collect_filenames_from_cached_torrent(hash)
    pprint(sorted(files_in_stream))


@app.command()
async def add_magnet(hash: str):
    rdbc = RealDebridClient(Config())
    await rdbc.add_magnet(hash)


@app.command()
async def new_oauth2():
    open_source_app_id = "X245A4XAIBGVM"
    base_url = "https://api.real-debrid.com/oauth/v2"
    credentials_url = f"{base_url}/device/credentials"

    client = httpx_client.AsyncOAuth2Client(client_id=open_source_app_id)
    auth_url, _ = client.create_authorization_url(f"{base_url}/device/code")
    response = httpx.get(auth_url).json()

    print(f"Go to {response['direct_verification_url']}")

    device_code = response["device_code"]
    resp = {"error": "init"}
    while "error" in resp:
        await anyio.sleep(5)
        resp = httpx.get(
            credentials_url,
            params={"client_id": open_source_app_id, "code": device_code},
        ).json()

    client_id, client_secret = resp["client_id"], resp["client_secret"]
    print(f"{client_id=}\n{client_secret=}\n{device_code=}")


@app.command()
async def get_new_tokens(
    client_id: str,
    client_secret: str,
    device_code: str,
):
    base_url = "https://api.real-debrid.com/oauth/v2"
    tokens_url = f"{base_url}/token"
    tokens = httpx.post(
        tokens_url,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "http://oauth.net/grant_type/device/1.0",
            "code": device_code,
        },
    ).json()
    print(tokens)
