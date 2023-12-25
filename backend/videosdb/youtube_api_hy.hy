;(import [__future__ [TailRec]])
(import videosdb.youtube-api)

(defn _request-one [url params use-cache])

(defn/a get-playlist-info [playlist-id]
  (await (_request-one "/playlists")))
