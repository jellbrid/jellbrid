# Jellbrid

A bridge between Jellyseerr, Jellyfin and Real-Debrid.

Periodically reads media requests off of Jellyseerr, finds the requested media,
and makes it available on Jellyfin.

> [!NOTE]  
> This project is inspired by itsToggle's project, `plex_debrid` and is revamped 
> replacement. It assumes that pd_zurg is running -- that is what actually makes 
> media in Real-Debrid available locally.

## Features
- Accepts request approval webhooks to instantly process new requests
- Support for identifying and selecting instantly available media on
  Real-Debrid, this means that it typically takes the length of a Jellyfin scan
  to make new media available
- Complete the gaps in your media requests with built in support for determining
  which episodes are missing and searching only for those
- Automatically updates quality profiles depending on how old the requested
  media is
- Automatically finds the highest quality media available
- Built in filtering system to make sure that the only media downloaded is the
  media that was requested
- Minimal API requests to external requests to prevent excessive traffic and
  rate limits from being hit
- Tracks downloads on Real-Debrid (on non-instanty available media) to prevent
  redundant downloads in your account

## Requirements
- A Real-Debrid account and API token
- A Jellyseerr instance and API token
- A Jellyfin instance and API token

Create a `.env` file with the following contents:

```bash
export JF_API_KEY=123
export JF_URL=http://localhost:8096
export SEERR_API_KEY=456
export SEERR_URL=http://localhost:5055
export RD_API_KEY=789
export RD_API_URL=https://api.real-debrid.com/rest/1.0/
export TORRENTIO_URL=https://torrentio.strem.fun
export JELLBRID_LOG_LEVEL=info
```

Install and then run it:
`uv sync && uv run cli jellbrid --loop`

## Docker compose

The project supports being run by docker compose. The secrets in the `.env` file should be set on the compose service. For an example, see the `compose.yml` file.

## Using webhooks

On Jellyseerr, go to `Notifications` -> `Webhooks` and set Webhook URL to the
address and port of your jellbrid server/container. It should look something
like `http://jellbrid:9090`. Then select "Request Automatically Approved" and
"Request Approved". 

## Dev

To run alembic:
uv run alembic --config ./src/jellbrid/storage/alembic/alembic.ini

### TODO
- auto remove redundant torrents
- auto update files to 4k
- keep track of stats:
  - number of torrentio requests per media request
  - number of RD requests per media request
- implement some sort of exponential backoff for requests that continuously just
  dont exist (like the looney toons seasons/episodes)
- implement some sort of backoff for downloads that fail
- implement a transparent, multitiered exponential backoff cache for requests
  that repeatedly are unable to be fulfilled