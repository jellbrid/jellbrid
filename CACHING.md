
# Caching counts for Media Requests

Torrentio
- 1 to Torrentio for streams

RD
- 1 to determine instantAvailability (if it is, this gets cached)

To download cached:
- 1 to RD to add magnet
# - 1 to get files
- 1 to select files
TOTAL: 4 API calls (1 Torrentio, 3 RD)
        2 API calls to check stream (1 Torrentio, 1 RD)

To download uncached:
- 1 to RD to add magnet
- 1 to RD to get file ids from torrent (this gets cached)
- 1 to RD to delete magnet
[check stream criteria]
- 1 to RD to add magnet
# - 1 to get files
- 1 to select files

TOTAL: 7 API calls (1 Torrentio, 6 RD)
        5 API calls to check stream (1 Torrentio, 4 RD)

Each MediaRequest = 1 (1 T)

Per stream:
    Cached - 1 (1 RD)
    Uncached - 4 (4 RD)

Download:
    Cached - 3 (3 RD) [Adds 2 on top of per stream]
    Uncached - 6 (6 RD) [Adds 2 on top of per stream] (this is because of the
    step to add the magnet, check the files, then delete it)


# Cache locations
- alru_cache TTL
    - RD (60 mins)
        - get_cached_torrent_data
          I'm caching this so that multiple lookups for a stream don't hit the
          RD API. We do ~2 in the course of a lookup: once to determine if the
          hash is cached, then again to pull the data for use. I think 30
          minutes is fine although it could be lower

    - Torrentio (1 hour)
        - streams for movies (by IMDB)
        - streams for shows (by IMDB, season #, episode #)

    ** NOTE ** The results that we get from torrentio are used directly in RD
    for looking up cached data. So it probably makes sense to keep those cache
    TTLs the same

  - TTLCache (60 mins)
    - Movie Requests
        - caches by IMDB ID IFF a non-cached download was initiated
    - Season Requests
        - caches by IMDB ID iff a non-cached download was initiated
    - Episode Requests
        - caches by IMDB ID- season ID - episode ID iff a non-cached download
          was initiated

    ** NOTE ** This cache is just used to make sure we aren't enqueueing the
    same request for a torrent that's downloading. The expectation with the TTL
    is that within TTL: 
      - the torrent will download 
      - jellyfin will have scanned the library
      - jellyfin will have successfully ID's the download
      - seer will have synced with jellyfin