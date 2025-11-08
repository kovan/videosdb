
;; ============================================================================
;; src/videosdb/downloader.clj - Main download orchestration (Functional)
;; ============================================================================

(ns videosdb.downloader
  (:require [clojure.tools.logging :as log]
            [clojure.core.async :as async]
            [clojure.data.json :as json]
            [clojure.string :as str]
            [videosdb.db :as db]
            [videosdb.youtube-api :as yt-api]
            [videosdb.utils :as utils]
            [videosdb.publisher :as publisher]
            [environ.core :refer [env]])
  (:import [java.util.concurrent.atomic AtomicBoolean AtomicReference]
           [java.util Date]
           [java.time Instant Duration]))

;; Video processor state management
(defn create-video-processor [channel-id]
  {:channel-id channel-id
   :video-to-playlist-list (AtomicReference. {})
   :quota-exceeded (AtomicBoolean. false)})

(defn add-video-to-processor! [processor video-id playlist-id]
  (log/debug (format "Processing playlist item video %s, playlist %s" video-id playlist-id))
  (let [videos-ref (:video-to-playlist-list processor)]
    (.updateAndGet videos-ref
                   (fn [videos]
                     (let [current-playlists (get videos video-id #{})]
                       (assoc videos video-id
                              (if playlist-id
                                (conj current-playlists playlist-id)
                                current-playlists)))))))

(defn create-video! [db-state processor video-id playlist-ids]
  (log/info (format "Writing video: %s..." video-id))
  (let [downloaded-video (when-not (.get (:quota-exceeded processor))
                           (try
                             (let [[_ vid] (yt-api/get-video-info video-id)]
                               vid)
                             (catch Exception e
                               (when (utils/handle-exception utils/quota-exceeded-type e log/error)
                                 (.set (:quota-exceeded processor) true))
                               nil)))]

    (when downloaded-video
      (let [channel-id-from-video (get-in downloaded-video [:snippet :channelId])]
        ;; Skip videos from other channels
        (when (= channel-id-from-video (:channel-id processor))
          (let [updated-video (-> downloaded-video
                                  (assoc :videosdb
                                         (merge (:videosdb downloaded-video {})
                                                {:slug (utils/slugify (get-in downloaded-video [:snippet :title]))
                                                 :descriptionTrimmed (get-in downloaded-video [:snippet :description])
                                                 :durationSeconds (utils/parse-duration (get-in downloaded-video [:contentDetails :duration]))}))
                                  (assoc-in [:snippet :publishedAt] (utils/parse-datetime (get-in downloaded-video [:snippet :publishedAt])))
                                  (update :statistics #(into {} (map (fn [[k v]] [k (Integer/parseInt (str v))]) %))))]

            (when (seq playlist-ids)
              (let [final-video (assoc-in updated-video [:videosdb :playlists] (vec playlist-ids))]
                (db/db-set! db-state (str "videos/" video-id) final-video true)))

            (log/info (format "Wrote video %s" video-id))
            updated-video))))))

(defn close-video-processor! [db-state processor]
  (let [videos (.get (:video-to-playlist-list processor))
        video-ids (keys videos)
        shuffled-ids (shuffle video-ids)]
    (log/info (format "Writing %s videos" (count video-ids)))
    (doseq [video-id shuffled-ids]
      (let [playlists (get videos video-id)]
        (create-video! db-state processor video-id playlists)))))

;; Task execution functions
(defn execute-export-task [db-state options video]
  (when (:export-to-emulator-host options)
    (log/debug "Would export to emulator:" (:id video))))

(defn execute-publish-task [db-state options video]
  (when (:enable-twitter-publishing options)
    (try
      (publisher/publish-video db-state video)
      (catch Exception e
        (log/error e "Publishing error")))))

(defn execute-transcript-task [db-state options video]
  (when (:enable-transcripts options)
    (let [current-status (get-in video [:videosdb :transcript_status])]
      (when (or (nil? current-status) (= current-status "pending"))
        (log/info "Would download transcript for video:" (:id video))))))

(defn execute-validation-task [db-state options video]
  (db/validate-video-schema db-state video))

;; Channel operations
(defn create-channel! [db-state channel-id]
  (let [[_ channel-info] (yt-api/get-channel-info channel-id)]
    (when channel-info
      (log/info (format "Processing channel: %s" (get-in channel-info [:snippet :title])))
      (db/db-set! db-state (str "channel_infos/" channel-id) channel-info true)
      channel-info)))

(defn retrieve-all-playlist-ids [channel-id]
  (let [[_ ids1] (yt-api/list-channelsection-playlist-ids channel-id)
        [_ ids2] (yt-api/list-channel-playlist-ids channel-id)
        all-ids (if (env :debug)
                  ids1
                  (concat ids1 ids2))
        playlist-ids (set all-ids)]
    (log/info "Retrieved all playlist IDs.")
    (vec playlist-ids)))

(defn create-playlist! [db-state playlist playlist-items channel-id & [write?]]
  (let [write? (if (nil? write?) true write?)
        filtered-items (filter #(= (get-in % [:snippet :channelId]) channel-id) playlist-items)
        video-count (count filtered-items)
        video-ids (->> filtered-items
                       (map #(get-in % [:snippet :resourceId :videoId]))
                       (set))
        last-updated (->> filtered-items
                          (map #(utils/parse-datetime (get-in % [:snippet :publishedAt])))
                          (filter identity)
                          (sort)
                          (last))
        updated-playlist (assoc playlist :videosdb
                                {:videoCount video-count
                                 :lastUpdated last-updated
                                 :videoIds video-ids
                                 :slug (utils/slugify (get-in playlist [:snippet :title]))})]

    (when write?
      (db/db-set! db-state (str "playlists/" (:id playlist)) updated-playlist true)
      (log/info (format "Wrote playlist: %s" (get-in playlist [:snippet :title]))))

    updated-playlist))

(defn process-playlist! [db-state playlist-id channel-name channel-id processor write?]
  (log/info (format "Processing playlist %s" playlist-id))
  (let [[_ playlist] (yt-api/get-playlist-info playlist-id)]
    (when (and playlist
               (= (get-in playlist [:snippet :channelTitle]) channel-name))
      (let [[_ playlist-items] (yt-api/list-playlist-items playlist-id)
            updated-playlist (create-playlist! db-state playlist playlist-items channel-id write?)
            video-ids (shuffle (vec (get-in updated-playlist [:videosdb :videoIds])))]

        (doseq [video-id video-ids]
          (add-video-to-processor! processor video-id (when write? playlist-id)))))))

;; Phase operations
(defn phase1! [db-state channel-id]
  (log/info "Init phase 1")
  (let [processor (create-video-processor channel-id)]
    (try
      (when-let [channel (create-channel! db-state channel-id)]
        (let [channel-name (get-in channel [:snippet :title])
              playlist-ids (retrieve-all-playlist-ids channel-id)
              shuffled-playlist-ids (shuffle playlist-ids)]

          ;; Process regular playlists
          (doseq [playlist-id shuffled-playlist-ids]
            (process-playlist! db-state playlist-id channel-name channel-id processor true))

          ;; Process all videos playlist
          (let [all-videos-playlist-id (get-in channel [:contentDetails :relatedPlaylists :uploads])]
            (when (and all-videos-playlist-id (not (env :debug)))
              (process-playlist! db-state all-videos-playlist-id channel-name channel-id processor false)))

          (close-video-processor! db-state processor)))
      (catch Exception e
        (utils/handle-exception utils/quota-exceeded-type e log/error)))))

(defn final-video-iteration! [db-state tasks]
  (let [final-video-ids (atom #{})]
    ;; Query videos collection for videos ready to publish
    (let [video-ids-doc (db/db-get-noquota db-state "meta/video_ids")
          video-ids (when (.exists video-ids-doc)
                      (get (.getData video-ids-doc) "videoIds" []))]
      (doseq [video-id video-ids]
        (try
          (let [video-doc (db/db-get-noquota db-state (str "videos/" video-id))]
            (when (.exists video-doc)
              (let [video-dict (.getData video-doc)]
                (when (not (empty? (get-in video-dict [:videosdb :slug])))
                  (swap! final-video-ids conj video-id)
                  (log/debug (format "Applying tasks for video %s" video-id))
                  (doseq [task-fn tasks]
                    (task-fn video-dict))))))
          (catch Exception e
            (log/error e (format "Error processing video %s" video-id)))))

      (let [final-ids @final-video-ids]
        (when (seq final-ids)
          (db/db-set-noquota! db-state "meta/video_ids"
                              {"videoIds" (vec final-ids)}))

        (when (empty? final-ids)
          (throw (Exception. "No videos to publish")))

        (log/info (format "Final video list length: %s" (count final-ids)))
        final-ids))))

(defn phase2! [db-state options]
  (log/info "Init phase 2")
  (let [tasks [(partial execute-transcript-task db-state options)
               (partial execute-publish-task db-state options)
               (partial execute-export-task db-state options)
               (partial execute-validation-task db-state options)]]

    (final-video-iteration! db-state tasks)))

;; Debug information
(defn print-debug-info [db-state & [once?]]
  (when-not once?
    (future
      (while true
        (log/info "DB stats:")
        (log/info (db/get-stats db-state))
        (log/info "Cache stats:")
        (log/info (yt-api/cache-stats))
        (Thread/sleep 120000))))

  (when once?
    (log/info "Final DB stats:")
    (log/info (db/get-stats db-state))
    (log/info "Final cache stats:")
    (log/info (yt-api/cache-stats))))

;; Main entry point
(defn check-for-new-videos [db-state options channel-id]
  (log/info "Sync start")
  (print-debug-info db-state)

  (try
    (phase1! db-state channel-id)
    (phase2! db-state options)
    (finally
      (print-debug-info db-state true)))

  (log/info "Sync finished"))