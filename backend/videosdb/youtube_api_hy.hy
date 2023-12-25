(import videosdb.youtube-api)



(defn/a get-playlist-info [playlist-id]
  (await (_request-one "/playlists")))
