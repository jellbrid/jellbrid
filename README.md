To be done:
- auto remove redundant torrents
- auto update files to 4k
- accept webhooks from seerrs to start a DL (instead of? in addition to? polling)
- make CTRL-C finish handling active requests
- make RDBC file selection rules pluggable (using some sort of list of filters)
  - RDBC
    - rdbc.has_cached(s["infoHash"]
    - if (len(files) / len(request.episodes)) < 0.8
    - if len(files) != 1
    - collecting filenames/fileids based on extension

  - TC
    - if not tc.contains_full_season(s, request.season_id) - X

- count how many requests are made per hash (or per stream) to RD and Torrentio


    Movie Request
      Torrentio
      - 1 to Torrentio for streams

      RD
      - 1 to get_cached_torrent_data (gets cached and used A LOT)
      - to download cached
        - 1 to RD to add magnet
        - 1 to get files (if uncached)
        - 1 to select files

      - to download uncached
        - 1 to RD to add magnet
        - 1 to RD to delete magnet
        - 1 to RD to get file ids from torrent
        [check stream criteria]
        - 1 to RD to add magnet
        - 1 to get files (if uncached)
        - 1 to select files

      - if stream is cached
        - no more
        
      - if stream is uncached
        - 1 to RD to add magnet
        - 1 to RD to delete magnet
        - 1 to RD to get file ids from torrent



      - per cached stream: 1
      - per uncached stream: 4
      - per download: 3

- implement uncached downloads by number of seeders
- implement JF + seer scans on uncached download completion
  - delete the download if it failed

- implement some sort of exponential backoff for requests that continuously just
  dont exist (like the looney toons seasons/episodes)

- make sure im caching in the right places
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

    That's all generally OK, but there needs to be a mechanism to run JF+seer
    scans. Also it would be great to more closely track a torrents DL status to
    not have to wait an hour for uncached downloads.

    Also, if the download failed, we probably DON"T want to try it again later
    on. It might just be busted frown -- TODO implement uncached downloads by
    number of seeders to mitigate this. 
    

Done:
- refactor clients to simplify / remove unnecessary methods / types - X
- have all clients create themselves from configs - X
- case: if you can't find a full season download, download individual episodes - X
- don't redownload uncached downloads - X
- support episode by episode downloads - X
    - Idea:
      The jellyseer request "get_show_details" response contains a field
      "jellyfinMediaId" that maps the show to to jellyfin. We can pull episode
      information from jellyfin (what we have) and compare to what's missing in
      Overseerr, giving us what we need