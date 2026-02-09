(ns videosdb.server.pathom
  "Pathom3 resolvers: Firestore -> Fulcro data."
  (:require [com.wsscode.pathom3.connect.operation :as pco]
            [com.wsscode.pathom3.connect.indexes :as pci]
            [com.wsscode.pathom3.interface.eql :as p.eql]
            [clojure.tools.logging :as log]
            [videosdb.firestore :as fs]
            [videosdb.app.model :as model]))

;; --- Resolvers ---

(pco/defresolver video-by-slug
  "Resolve a video by its slug."
  [{:keys [db]} {:video/keys [slug]}]
  {::pco/input  [:video/slug]
   ::pco/output [:video/id :video/title :video/description
                 :video/description-trimmed :video/published-at
                 :video/channel-id :video/channel-title
                 :video/thumbnail-url :video/duration
                 :video/duration-seconds :video/slug
                 :video/view-count :video/like-count
                 :video/comment-count :video/favorite-count
                 :video/tags :video/playlists :video/embed-url
                 :video/content-details-duration :video/raw]}
  (let [videos (fs/query-where db "videos" "videosdb.slug" :== slug)]
    (when (seq videos)
      (model/firestore-video->entity (first videos)))))

(pco/defresolver video-by-id
  "Resolve a video by its ID."
  [{:keys [db]} {:video/keys [id]}]
  {::pco/input  [:video/id]
   ::pco/output [:video/id :video/title :video/description
                 :video/description-trimmed :video/published-at
                 :video/channel-id :video/channel-title
                 :video/thumbnail-url :video/duration
                 :video/duration-seconds :video/slug
                 :video/view-count :video/like-count
                 :video/comment-count :video/favorite-count
                 :video/tags :video/playlists :video/embed-url
                 :video/content-details-duration :video/raw]}
  (let [doc (fs/get-doc db (str "videos/" id))]
    (when doc
      (model/firestore-video->entity doc))))

(pco/defresolver playlist-by-slug
  "Resolve a playlist by its slug."
  [{:keys [db]} {:playlist/keys [slug]}]
  {::pco/input  [:playlist/slug]
   ::pco/output [:playlist/id :playlist/title :playlist/description
                 :playlist/thumbnail-url :playlist/slug
                 :playlist/video-count :playlist/last-updated
                 :playlist/video-ids :playlist/raw]}
  (let [playlists (fs/query-where db "playlists" "videosdb.slug" :== slug)]
    (when (seq playlists)
      (model/firestore-playlist->entity (first playlists)))))

(pco/defresolver all-playlists
  "Resolve all playlists (categories), ordered by lastUpdated desc."
  [{:keys [db]} _]
  {::pco/output [{:all-playlists [:playlist/id :playlist/title
                                   :playlist/slug :playlist/video-count
                                   :playlist/last-updated]}]}
  (let [docs (fs/query-collection db "playlists")]
    {:all-playlists
     (->> docs
          (map model/firestore-playlist->entity)
          (sort-by :playlist/last-updated #(compare %2 %1))
          vec)}))

(pco/defresolver video-list
  "Paginated video list for the Explorer."
  [{:keys [db]} {:keys [order-field order-direction
                        category-id tag limit-n]}]
  {::pco/output [{:video-list [:video/id :video/title
                                :video/thumbnail-url :video/published-at
                                :video/duration-seconds :video/slug]}]}
  (let [opts (cond-> {:order-by [(or order-field "snippet.publishedAt")
                                 (if (= order-direction "asc") :asc :desc)]
                      :limit   (or limit-n 20)}
               category-id
               (assoc :where-clause ["videosdb.playlists" :array-contains category-id])

               tag
               (assoc :where-clause ["snippet.tags" :array-contains tag]))
        docs (fs/query-videos db opts)]
    {:video-list (mapv model/firestore-video->entity docs)}))

(pco/defresolver meta-video-ids
  "Resolve the meta/video_ids document."
  [{:keys [db]} _]
  {::pco/output [:meta/video-ids]}
  (let [doc (fs/get-doc db "meta/video_ids")]
    {:meta/video-ids (:videoIds doc [])}))

(pco/defresolver playlist-details
  "Resolve full playlist details by ID (for video page category cards)."
  [{:keys [db]} {:playlist/keys [id]}]
  {::pco/input  [:playlist/id]
   ::pco/output [:playlist/id :playlist/title :playlist/description
                 :playlist/thumbnail-url :playlist/slug
                 :playlist/video-count :playlist/last-updated
                 :playlist/raw]}
  (let [doc (fs/get-doc db (str "playlists/" id))]
    (when doc
      (model/firestore-playlist->entity doc))))

;; --- Pathom environment ---

(def resolvers
  [video-by-slug video-by-id playlist-by-slug
   all-playlists video-list meta-video-ids
   playlist-details])

(defn make-env
  "Create a Pathom3 environment with the given Firestore client."
  [db]
  (let [env (pci/register resolvers)]
    (assoc env :db db)))

(defn process
  "Process an EQL query against the Pathom environment."
  [env query]
  (p.eql/process env query))
