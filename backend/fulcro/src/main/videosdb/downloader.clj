(ns videosdb.downloader
  "Two-phase sync orchestrator. Replaces downloader.py."
  (:require [clojure.tools.logging :as log]
            [clojure.string :as str]
            [clojure.set :as set]
            [videosdb.config :as config]
            [videosdb.firestore :as fs]
            [videosdb.youtube-api :as yt])
  (:import [java.time Duration]
           [java.time.format DateTimeFormatter]
           [java.time Instant ZonedDateTime ZoneOffset]))

;; --- Slug generation ---

(defn slugify
  "Generate a URL-friendly slug from a title."
  [title]
  (when title
    (-> title
        str/lower-case
        (str/replace #"[^\p{L}\p{N}\s-]" "")
        str/trim
        (str/replace #"[\s]+" "-")
        (str/replace #"-+" "-")
        (str/replace #"^-|-$" ""))))

;; --- Duration parsing ---

(defn parse-duration-seconds
  "Parse ISO 8601 duration string to seconds. E.g. 'PT1H2M3S' -> 3723.0"
  [duration-str]
  (try
    (when duration-str
      (double (.getSeconds (Duration/parse duration-str))))
    (catch Exception e
      (log/warn "Failed to parse duration:" duration-str)
      0.0)))

;; --- Description trimming ---

(defn linkify-description
  "Convert URLs in description to clickable links (basic HTML linkification)."
  [description]
  (when description
    (str/replace description
                 #"(https?://[^\s<]+)"
                 "<a href=\"$1\" rel=\"nofollow\">$1</a>")))

;; --- ISO date parsing ---

(defn parse-iso-datetime
  "Parse ISO 8601 datetime string to java.util.Date."
  [date-str]
  (when date-str
    (try
      (java.util.Date/from (Instant/parse date-str))
      (catch Exception _
        (try
          (java.util.Date/from
           (.toInstant (ZonedDateTime/parse date-str)))
          (catch Exception _
            (log/warn "Failed to parse date:" date-str)
            nil))))))

;; --- Video processor ---

(defn- create-video
  "Download video info and write to Firestore."
  [db yt-client video-id playlist-ids channel-id quota-exceeded?]
  (log/info "Writing video:" video-id "...")
  (let [video (atom {})
        downloaded (atom nil)]
    (when-not @quota-exceeded?
      (try
        (let [[_ video-info] (yt/get-video-info yt-client video-id)]
          (when video-info
            (reset! downloaded video-info)
            (swap! video merge video-info)))
        (catch Exception e
          (if (yt/quota-exceeded? e)
            (do (log/error "YouTube quota exceeded")
                (reset! quota-exceeded? true))
            (log/error e "Error downloading video" video-id)))))

    (when (seq @video)
      (let [v @video]
        ;; Skip videos from other channels
        (when (or (nil? @downloaded)
                  (= (get-in v [:snippet :channelId]) channel-id))
          (let [videosdb-fields
                (cond-> {}
                  (and @downloaded (= (get-in v [:snippet :channelId]) channel-id))
                  (merge {:slug              (slugify (get-in v [:snippet :title]))
                          :descriptionTrimmed (linkify-description (get-in v [:snippet :description]))
                          :durationSeconds   (parse-duration-seconds
                                              (get-in v [:contentDetails :duration]))})

                  (seq playlist-ids)
                  (assoc :playlists (vec playlist-ids)))

                ;; Parse publishedAt to Date
                published-at (get-in v [:snippet :publishedAt])
                parsed-date  (when (string? published-at)
                               (parse-iso-datetime published-at))

                ;; Convert statistics to integers
                stats        (when-let [s (:statistics v)]
                               (into {} (map (fn [[k val]]
                                               [k (if (string? val) (Long/parseLong val) val)])
                                             s)))

                final-video  (cond-> v
                               (seq videosdb-fields)
                               (assoc :videosdb videosdb-fields)

                               parsed-date
                               (assoc-in [:snippet :publishedAt] parsed-date)

                               stats
                               (assoc :statistics stats))]

            (fs/set-doc db (str "videos/" video-id) final-video {:merge? true})
            (log/info "Wrote video" video-id)
            final-video))))))

;; --- Playlist processing ---

(defn- create-playlist
  "Process a playlist and write to Firestore."
  [db yt-client playlist playlist-items channel-id write?]
  (let [video-count (atom 0)
        last-updated (atom nil)
        video-ids   (atom #{})]

    (doseq [item playlist-items]
      (when (= (get-in item [:snippet :channelId]) channel-id)
        (let [vid (get-in item [:snippet :resourceId :videoId])]
          (swap! video-ids conj vid)
          (swap! video-count inc)
          (let [date (parse-iso-datetime (get-in item [:snippet :publishedAt]))]
            (when (and date (or (nil? @last-updated)
                                (.after date @last-updated)))
              (reset! last-updated date))))))

    (let [enriched (assoc playlist :videosdb
                          {:videoCount  @video-count
                           :lastUpdated @last-updated
                           :videoIds    @video-ids
                           :slug        (slugify (get-in playlist [:snippet :title]))})]
      (when write?
        (fs/set-doc db (str "playlists/" (:id playlist)) enriched {:merge? true})
        (log/info "Wrote playlist:" (get-in playlist [:snippet :title])))
      enriched)))

(defn- process-playlist
  "Process a single playlist: fetch info, items, create playlist, collect videos."
  [db yt-client playlist-id channel-name video-to-playlists channel-id write?]
  (log/info "Processing playlist" playlist-id)
  (let [[_ playlist] (yt/get-playlist-info yt-client playlist-id)]
    (when playlist
      (when (= (get-in playlist [:snippet :channelTitle]) channel-name)
        (let [[_ playlist-items] (yt/list-playlist-items yt-client playlist-id)
              enriched (create-playlist db yt-client playlist
                                       (vec playlist-items) channel-id write?)]
          ;; Collect video -> playlist mappings
          (doseq [vid (:videoIds (:videosdb enriched))]
            (swap! video-to-playlists update vid
                   (fnil conj #{}) (when write? playlist-id))))))))

;; --- Main sync phases ---

(defn- retrieve-all-playlist-ids
  "Get all unique playlist IDs for a channel."
  [yt-client channel-id]
  (let [[_ section-ids] (yt/list-channelsection-playlist-ids yt-client channel-id)
        [_ channel-ids] (yt/list-channel-playlist-ids yt-client channel-id)]
    (log/info "Retrieved all playlist IDs.")
    (vec (distinct (concat section-ids channel-ids)))))

(defn- phase1
  "Phase 1: Fetch channel/playlists/videos from YouTube API, write to Firestore."
  [db yt-client channel-id]
  (log/info "Init phase 1")
  (let [video-to-playlists (atom {})
        quota-exceeded?    (atom false)]
    (try
      (let [[_ channel-info] (yt/get-channel-info yt-client channel-id)]
        (when channel-info
          (let [channel-name (get-in channel-info [:snippet :title])]
            (log/info "Processing channel:" channel-name)
            (fs/set-doc db (str "channel_infos/" channel-id) channel-info {:merge? true})

          ;; Get all playlist IDs
          (let [playlist-ids (retrieve-all-playlist-ids yt-client channel-id)]
            ;; Process playlists concurrently
            (let [futures (doall
                           (map (fn [pid]
                                  (future
                                    (try
                                      (process-playlist db yt-client pid
                                                        channel-name video-to-playlists
                                                        channel-id true)
                                      (catch Exception e
                                        (log/error e "Error processing playlist" pid)))))
                                (shuffle playlist-ids)))]
              (doseq [f futures] @f))

            ;; Process "all videos" playlist (uploads)
            (let [uploads-id (get-in channel-info [:contentDetails :relatedPlaylists :uploads])]
              (when uploads-id
                (process-playlist db yt-client uploads-id
                                  channel-name video-to-playlists
                                  channel-id false))))

          ;; Write all videos
          (let [all-videos @video-to-playlists
                video-ids  (shuffle (keys all-videos))]
            (log/info "Writing" (count video-ids) "videos")
            (let [futures (doall
                           (map (fn [vid]
                                  (future
                                    (try
                                      (create-video db yt-client vid
                                                    (get all-videos vid)
                                                    channel-id quota-exceeded?)
                                      (catch Exception e
                                        (log/error e "Error creating video" vid)))))
                                video-ids))]
              (doseq [f futures] @f))))))
      (catch Exception e
        (if (= :quota-exceeded (:type (ex-data e)))
          (log/error "Quota exceeded:" (ex-message e))
          (throw e))))))

(defn- phase2
  "Phase 2: Validate schemas, write meta/video_ids."
  [db]
  (log/info "Init phase 2")
  (let [videos       (fs/query-where db "videos" "videosdb.slug" :!= "")
        final-ids    (atom #{})]

    (doseq [video videos]
      (let [video-id (:id video)]
        (when video-id
          (swap! final-ids conj video-id)
          (log/debug "Processing video for phase 2:" video-id))))

    (let [ids @final-ids]
      (when (empty? ids)
        (throw (ex-info "No videos to publish" {})))

      (fs/set-doc db "meta/video_ids"
                  {:videoIds (vec ids)}
                  {:no-quota? true})

      (log/info "Final video list length:" (count ids))
      ids)))

;; --- Public API ---

(defn check-for-new-videos
  "Main entry point: run Phase 1 then Phase 2."
  ([] (check-for-new-videos {}))
  ([{:keys [channel-id redis-db-n]}]
   (let [channel-id (or channel-id (config/env "YOUTUBE_CHANNEL_ID"))
         db         (fs/create-client)
         yt-client  (yt/make-client {:redis-db-n redis-db-n})]

     (log/info "Sync start")
     (fs/init-meta! db)

     (try
       (phase1 db yt-client channel-id)
       (phase2 db)
       (finally
         (log/info "DB stats:" (fs/get-stats))))

     (log/info "Sync finished"))))
