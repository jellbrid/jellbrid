# Jellbrid

A bridge between Jellyseerr, Jellyfin and Real-Debrid.

Periodically reads media requests off of Jellyseerr, finds the requested media,
and makes it available on Jellyfin.

## Features
- Support for identifying and selecting instantly available media on
  Real-Debrid, this means that it typically takes the length of a Jellyfin scan
  to make new media available
- Complete the gaps in your media requests with built in support for determining
  which episodes are missing and finding only those
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
export SEERR_API_KEY=123
export SEERR_URL=http://localhost:5055
export RD_API_KEY=123
export RD_API_URL=https://api.real-debrid.com/rest/1.0/
export TORRENTIO_URL=https://torrentio.strem.fun
export JELLBRID_LOG_LEVEL=info
```

Install and then run it:
`uv sync && uv run cli jellbrid`

### TODO
- track requests to prevent duplicate downloads when JF doesn't immedediately
  recognize media
- auto remove redundant torrents
- auto update files to 4k
- accept webhooks from seerrs to start a DL (instead of? in addition to? polling)
- make CTRL-C finish handling active requests
- keep track of stats:
  # of torrentio requests per media request
  # of of RD requests per media request
- implement some sort of exponential backoff for requests that continuously just
  dont exist (like the looney toons seasons/episodes)
- implement some sort of backoff for downloads that fail

### Done
- implement uncached downloads by number of seeders - X
- count how many requests are made to RD and Torrentio
- refactor clients to simplify / remove unnecessary methods / types
- have all clients create themselves from configs
- case: if you can't find a full season download, download individual episodes
- don't redownload uncached downloads
- support episode by episode downloads
    - Idea:
      The jellyseer request "get_show_details" response contains a field
      "jellyfinMediaId" that maps the show to to jellyfin. We can pull episode
      information from jellyfin (what we have) and compare to what's missing in
      Overseerr, giving us what we need
- TODO: inspect the RD cached results more closely. sometimes, the
  instantAvailability results contain a sub-dict of files that seems to indicate
  that files within that subdict could be instantly-downloaded separately from
  everything else. i.e. "fba8d22d247726db32dc03911984008315656856" - X
- make RDBC file selection rules pluggable - X
  - RDBC
    - rdbc.has_cached(s["infoHash"]
    - if (len(files) / len(request.episodes)) < 0.8
    - if len(files) != 1
    - collecting filenames/fileids based on extension
  - TC
    - if not tc.contains_full_season(s, request.season_id) - X
- filter titles with short/common names with their release year (i.e. Haunt) - X 
- allow older series to have worse quality profiles - X
- implement JF + seer scans on uncached download completion
  - delete the download if it failed
  - this could probably just be a task that iterates thru the cache contents and
    checks their status. deleting if the seeders is None. and then using a
    secondary cache to make that request unavailable for a while? - X