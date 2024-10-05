
# API call for Media Requests

## Downloading a cached MediaRequest 

5 requests [1 Torrentio, 4 RD]

- 1 Torrentio: get candidate streams
- 1 RD: determine instant availability for all streams
- 1 RD: add magnet
- 1 RD: get files [cached]
- 1 RD: select files

## Downloading an uncached MediaRequest 

4 requests [1 Torrentio, 3 RD] + 3 * Streams [RD]

- 1 Torrentio: get candidate streams
- 1 RD: determine instant availability for all streams
- 1 RD: add magnet         -|
- 1 RD: get files [cached]  |--- repeated for every stream
- 1 RD: delete magnet      -|
- 1 RD: add magnet
- 1 RD: select files

# Cache locations
- TTLCache 
  - RD (60 minutes)
    - get_instant_availability_data
        
        Each hash is individually cached so that if we do either a single lookup
        / a bulk lookup, hashes that are cached are not queried for. This is
        used to determine if the hash is cached on RD and then again for file
        filtering and selection.
        
  - Torrentio (60 minutes)
    - get_show_streams (IMDB-season-episode)
    - get_movie_streams (IMDB)
    
  ** NOTE ** The results from Torrentio are used directly in RD for looking up
  instantly available data, so it makes sense to keep those cache TTLs the same 

- TTLCache 
  - Seerrs (60 mins)
    - checks if each request is in the cache. Requests are cached if an non
      instantly available download begins. 

    - MovieRequests are (IMDB), EpisodeRequests are (IMDB-season-episode)

    ** NOTE ** This cache is just used to make sure we aren't enqueueing the
    same request for a torrent that's downloading. The expectation with the TTL
    is that within TTL: 
      - the torrent will download 
      - jellyfin will have scanned the library
      - jellyfin will have successfully ID's the download
      - seer will have synced with jellyfin