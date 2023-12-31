




(defn/a get-playlist-info [api playlist-id]
  (await (api._request-one
          "/playlists"
          {"part" "snippet"
           "id" playlist-id})))

(defn/a list-channelsection-playlist-ids [api channel-id]
  (defn/a generator [results]
    (setv filtered-results
      (filter fn [item]
              (and (get item "contentDetails")
                   (get (get item "contentDetails") "playlists"))))

    (gfor :async filtered-results item (get item "id"))))




