### TODO
- allow older series to have worse quality profiles 
- auto remove redundant torrents
- auto update files to 4k
- accept webhooks from seerrs to start a DL (instead of? in addition to? polling)
- make CTRL-C finish handling active requests
- keep track of stats:
  # of torrentio requests per media request
  # of of RD requests per media request
- implement JF + seer scans on uncached download completion
  - delete the download if it failed
  - this could probably just be a task that iterates thru the cache contents and
    checks their status. deleting if the seeders is None. and then using a
    secondary cache to make that request unavailable for a while?
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
