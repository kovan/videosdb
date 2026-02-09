(ns videosdb.app.model
  "Fulcro data model: idents, queries, and initial state."
  (:require [com.fulcrologic.fulcro.components :as comp :refer [defsc]]
            [com.fulcrologic.fulcro.algorithms.merge :as merge]))

;; --- Video entity ---
(defsc Video [this props]
  {:ident :video/id
   :query [:video/id
           :video/title
           :video/description
           :video/description-trimmed
           :video/published-at
           :video/channel-id
           :video/channel-title
           :video/thumbnail-url
           :video/duration
           :video/duration-seconds
           :video/slug
           :video/view-count
           :video/like-count
           :video/comment-count
           :video/favorite-count
           :video/tags
           :video/playlists
           :video/embed-url
           :video/content-details-duration
           ;; Raw Firestore data for SSG
           :video/raw]})

;; --- Playlist (Category) entity ---
(defsc Playlist [this props]
  {:ident :playlist/id
   :query [:playlist/id
           :playlist/title
           :playlist/description
           :playlist/thumbnail-url
           :playlist/slug
           :playlist/video-count
           :playlist/last-updated
           :playlist/video-ids
           :playlist/raw]})

;; --- Meta entity ---
(defsc Meta [this props]
  {:ident :meta/id
   :query [:meta/id
           :meta/video-ids]})

;; --- Converters: Firestore doc -> Fulcro entity ---

(defn firestore-video->entity
  "Convert a raw Firestore video document to a Fulcro video entity."
  [doc]
  (let [snippet    (:snippet doc)
        stats      (:statistics doc)
        videosdb   (:videosdb doc)
        content    (:contentDetails doc)]
    {:video/id                      (:id doc)
     :video/title                   (:title snippet)
     :video/description             (:description snippet)
     :video/description-trimmed     (:descriptionTrimmed videosdb)
     :video/published-at            (:publishedAt snippet)
     :video/channel-id              (:channelId snippet)
     :video/channel-title           (:channelTitle snippet)
     :video/thumbnail-url           (get-in snippet [:thumbnails :medium :url])
     :video/duration                (:duration content)
     :video/duration-seconds        (:durationSeconds videosdb)
     :video/slug                    (:slug videosdb)
     :video/view-count              (:viewCount stats)
     :video/like-count              (:likeCount stats)
     :video/comment-count           (:commentCount stats)
     :video/favorite-count          (:favoriteCount stats)
     :video/tags                    (:tags snippet)
     :video/playlists               (:playlists videosdb)
     :video/embed-url               (str "https://www.youtube.com/watch?v=" (:id doc))
     :video/content-details-duration (:duration content)
     :video/raw                     doc}))

(defn firestore-playlist->entity
  "Convert a raw Firestore playlist document to a Fulcro playlist entity."
  [doc]
  (let [snippet  (:snippet doc)
        videosdb (:videosdb doc)]
    {:playlist/id           (:id doc)
     :playlist/title        (:title snippet)
     :playlist/description  (:description snippet)
     :playlist/thumbnail-url (get-in snippet [:thumbnails :medium :url])
     :playlist/slug         (:slug videosdb)
     :playlist/video-count  (:videoCount videosdb)
     :playlist/last-updated (:lastUpdated videosdb)
     :playlist/video-ids    (:videoIds videosdb)
     :playlist/raw          doc}))
