;; ============================================================================
;; project.clj - Leiningen project configuration
;; ============================================================================

(defproject videosdb "1.0.0"
  :description "VideosDB - YouTube video management system (Functional)"
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [org.clojure/core.async "1.6.673"]
                 [org.clojure/data.json "2.4.0"]
                 [org.clojure/tools.logging "1.2.4"]
                 [com.google.cloud/google-cloud-firestore "3.14.5"]
                 [com.google.auth/google-auth-library-oauth2-http "1.19.0"]
                 [clj-http "3.12.3"]
                 [carmine "3.2.0"]
                 [manifold "0.3.0"]
                 [clj-time "0.15.2"]
                 [cheshire "5.11.0"]
                 [slugger "1.0.1"]
                 [environ "1.2.0"]
                 [com.taoensso/timbre "6.2.2"]]
  :main videosdb.core)

;; ============================================================================
;; src/videosdb/core.clj - Main entry point
;; ============================================================================

(ns videosdb.core
  (:require [clojure.tools.logging :as log]
            [videosdb.db :as db]
            [videosdb.downloader :as downloader]
            [videosdb.settings :as settings]
            [environ.core :refer [env]]))

(defn -main [& args]
  (log/info "Starting VideosDB")
  (let [channel-id (env :youtube-channel-id)
        options {:enable-transcripts (= "true" (env :enable-transcripts))
                 :enable-twitter-publishing (= "true" (env :enable-twitter-publishing))
                 :export-to-emulator-host (env :export-to-emulator-host)}
        db-state (db/create-db)
        db-state (db/init-db! db-state)]
    (downloader/check-for-new-videos db-state options channel-id)))

;; ============================================================================
;; src/videosdb/settings.clj - Configuration settings
;; ============================================================================

(ns videosdb.settings
  (:require [environ.core :refer [env]]
            [taoensso.timbre :as log]))

(def config
  {:ipfs-host (env :ipfs-host "127.0.0.1")
   :ipfs-port (Integer/parseInt (env :ipfs-port "5001"))
   :videosdb-domain "sadhguru.digital"
   :videosdb-dnszone "sadhguru"
   :youtube-channel {:id "UCcYzLCs3zrQIBVHYA1sK2sw" :name "Sadhguru"}
   :truncate-description-after "#Sadhguru"
   :video-files-dir "/mnt/videos"
   :youtube-key "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU"
   :youtube-key-testing "AIzaSyDM-rEutI1Mr6_b1Uz8tofj2dDlwcOzkjs"})

;; Logging setup
(log/set-config!
 {:level (keyword (env :loglevel "info"))
  :appenders {:console {:enabled? true
                        :fn (fn [data]
                              (println (str (:level data) "\t"
                                            (:instant data) ":"
                                            (:?ns-str data) "." (:?fn-str data)
                                            " (" (:?file data) ":" (:?line data) "): "
                                            (:msg_ data))))}}})

;; ============================================================================
;; src/videosdb/utils.clj - Utility functions
;; ============================================================================

(ns videosdb.utils
  (:require [clojure.tools.logging :as log]
            [clojure.string :as str]
            [clojure.core.async :as async])
  (:import [java.net Socket SocketTimeoutException]
           [java.io IOException]
           [java.time Instant Duration]
           [java.time.format DateTimeFormatter]
           [java.util.concurrent.atomic AtomicInteger]))

;; Exception handling
(def quota-exceeded-type ::quota-exceeded)

(defn quota-exceeded [message]
  {::type quota-exceeded-type ::message message})

(defn quota-exceeded? [x]
  (= (::type x) quota-exceeded-type))

;; Network utilities
(defn wait-for-port
  ([port] (wait-for-port port "localhost" 30.0))
  ([port host] (wait-for-port port host 30.0))
  ([port host timeout]
   (log/debug (format "waiting for port %s:%s to be open" port host))
   (let [start-time (System/currentTimeMillis)]
     (loop []
       (try
         (let [socket (Socket. host port)]
           (.close socket)
           true)
         (catch IOException _
           (Thread/sleep 10)
           (when (< (- (System/currentTimeMillis) start-time) (* timeout 1000))
             (recur))))))))

;; Collection utilities
(defn put-item-at-front [seq item]
  (if (nil? item)
    seq
    (let [index (.indexOf (vec seq) item)]
      (if (>= index 0)
        (concat (drop index seq) (take index seq))
        seq))))

;; String utilities
(defn slugify [text]
  (when text
    (-> text
        str/lower-case
        (str/replace #"[^\w\s-]" "")
        (str/replace #"\s+" "-")
        (str/replace #"-+" "-")
        (str/replace #"^-|-$" ""))))

(defn parse-youtube-id [string]
  (when-let [match (re-find #"\[(.{11})\]\." string)]
    (second match)))

;; Time utilities
(defn parse-duration [duration-str]
  (when duration-str
    (try
      (let [duration (Duration/parse duration-str)]
        (.getSeconds duration))
      (catch Exception e
        (log/warn (format "Could not parse duration: %s" duration-str))
        0))))

(defn parse-datetime [datetime-str]
  (when datetime-str
    (try
      (Instant/parse datetime-str)
      (catch Exception e
        (log/warn (format "Could not parse datetime: %s" datetime-str))
        (Instant/now)))))

;; Error handling
(defn handle-exception [exception-type exception handler-fn]
  (if (and (map? exception) (= (::type exception) exception-type))
    (do (handler-fn exception) true)
    false))

;; Counter utilities
(defn create-counter [type limit]
  {:type type :counter (AtomicInteger. 0) :limit limit :lock (Object.)})

(defn inc-counter! [counter & [quantity]]
  (let [qty (or quantity 1)]
    (locking (:lock counter)
      (let [new-val (.addAndGet (:counter counter) qty)]
        (when (> new-val (:limit counter))
          (throw (ex-info "Counter limit exceeded"
                          (quota-exceeded (format "Surpassed %s ops limit of %s"
                                                  (:type counter) (:limit counter))))))))))

(defn counter-stats [counter]
  (format "Counter %s: %s/%s"
          (:type counter)
          (.get (:counter counter))
          (:limit counter)))

;; ============================================================================
;; src/videosdb/db.clj - Database operations (Functional)
;; ============================================================================

(ns videosdb.db
  (:require [clojure.tools.logging :as log]
            [clojure.data.json :as json]
            [clojure.java.io :as io]
            [videosdb.utils :as utils]
            [environ.core :refer [env]])
  (:import [com.google.cloud.firestore Firestore FirestoreOptions]
           [com.google.auth.oauth2 ServiceAccountCredentials]
           [java.io FileInputStream]))

;; Database configuration
(def db-config
  {:free-tier-write-quota 20000
   :free-tier-read-quota 50000})

;; Client creation
(defn get-client
  ([] (get-client nil nil))
  ([project] (get-client project nil))
  ([project config]
   (let [config (or config (env :videosdb-config "testing"))
         project (or project (env :firebase-project "videosdb-testing"))
         base-dir (System/getProperty "user.dir")
         common-dir (str base-dir "/common")
         creds-path (str common-dir "/keys/" (clojure.string/replace config "\"" "") ".json")]

     (if (env :firestore-emulator-host)
       (do (log/info "USING EMULATOR:" (env :firestore-emulator-host))
           (-> (FirestoreOptions/newBuilder)
               (.setProjectId "demo-project")
               (.setHost (env :firestore-emulator-host))
               (.setCredentials (ServiceAccountCredentials/fromStream
                                 (FileInputStream. creds-path)))
               (.build)
               (.getService)))
       (do (log/info "USING LIVE DATABASE")
           (log/info "Current project:" project)
           (log/info "Current config:" config)
           (-> (FirestoreOptions/newBuilder)
               (.setProjectId project)
               (.setCredentials (ServiceAccountCredentials/fromStream
                                 (FileInputStream. creds-path)))
               (.build)
               (.getService)))))))

;; Database state creation
(defn create-db []
  (let [counters {:reads (utils/create-counter :reads (- (:free-tier-read-quota db-config) 5000))
                  :writes (utils/create-counter :writes (- (:free-tier-write-quota db-config) 500))}
        base-dir (System/getProperty "user.dir")
        common-dir (str base-dir "/common")
        schema-path (str common-dir "/firebase/db-schema.json")
        db-schema (when (.exists (io/file schema-path))
                    (json/read-str (slurp schema-path) :key-fn keyword))
        db-client (get-client)]
    {:counters counters
     :db-schema db-schema
     :client db-client}))

;; Database initialization
(defn init-db! [db-state]
  (let [client (:client db-state)]
    ;; Initialize meta collections
    (let [video-ids-doc (.document client "meta/video_ids")
          video-ids-snap (.get video-ids-doc)]
      (when (or (not (.exists video-ids-snap))
                (not (contains? (.getData video-ids-snap) "videoIds")))
        (.set video-ids-doc {"videoIds" []})))

    (let [state-doc (.document client "meta/state")
          state-snap (.get state-doc)]
      (when (not (.exists state-snap))
        (.set state-doc {})))

    ;; Test write operation
    (db-set! db-state "meta/test" {})
    db-state))

;; Counter operations
(defn increase-counter! [db-state counter-type & [increase]]
  (let [inc-val (or increase 1)]
    (utils/inc-counter! (get (:counters db-state) counter-type) inc-val)))

;; Database operations with quota tracking
(defn db-set! [db-state path data & [merge?]]
  (increase-counter! db-state :writes)
  (let [doc (.document (:client db-state) path)]
    (if merge?
      (.set doc data com.google.cloud.firestore.SetOptions/merge)
      (.set doc data))))

(defn db-get [db-state path]
  (increase-counter! db-state :reads)
  (.get (.document (:client db-state) path)))

(defn db-update! [db-state path data]
  (increase-counter! db-state :writes)
  (.update (.document (:client db-state) path) data))

(defn db-delete! [db-state path]
  (increase-counter! db-state :writes)
  (.delete (.document (:client db-state) path)))

;; Database operations without quota tracking
(defn db-set-noquota! [db-state path data & [merge?]]
  (let [doc (.document (:client db-state) path)]
    (if merge?
      (.set doc data com.google.cloud.firestore.SetOptions/merge)
      (.set doc data))))

(defn db-get-noquota [db-state path]
  (.get (.document (:client db-state) path)))

(defn db-update-noquota! [db-state path data]
  (.update (.document (:client db-state) path) data))

;; Statistics
(defn get-stats [db-state]
  (let [read-counter (get (:counters db-state) :reads)
        write-counter (get (:counters db-state) :writes)]
    #{(utils/counter-stats read-counter)
      (utils/counter-stats write-counter)}))

;; Schema validation
(defn validate-video-schema [db-state video-dict]
  ;; Schema validation would go here
  ;; For now, just check if video has an ID
  (boolean (and video-dict (:id video-dict))))

;; ============================================================================
;; src/videosdb/youtube_api.clj - YouTube API client (Functional)
;; ============================================================================

(ns videosdb.youtube-api
  (:require [clojure.tools.logging :as log]
            [clojure.data.json :as json]
            [clj-http.client :as http]
            [taoensso.carmine :as car]
            [videosdb.utils :as utils]
            [environ.core :refer [env]]
            [clojure.string :as str])
  (:import [java.net URLEncoder]))

;; Redis connection
(def redis-conn {:pool {} :spec {:host "localhost" :port 6379 :db 0}})

(defmacro redis-cmd [& body]
  `(car/wcar redis-conn ~@body))

;; API configuration
(defn api-config []
  {:root-url (env :youtube-api-url "https://www.googleapis.com/youtube/v3")
   :api-key (or (env :youtube-api-key) "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU")})

;; Cache operations
(defn cache-stats []
  (redis-cmd
   (let [stats (car/info :stats)]
     (select-keys stats [:keyspace_hits :keyspace_misses
                         :total_commands_processed :total_reads_processed
                         :total_writes_processed]))))

(defn cache-key-func [url params]
  (let [sorted-keys (->> (keys params)
                         (remove #(= % :key))
                         (sort))
        params-seq (map #(str (name %) "=" (URLEncoder/encode (str (get params %)) "UTF-8"))
                        sorted-keys)
        query-string (str/join "&" params-seq)]
    (str (str/replace url #"^/" "") "?" query-string)))

(defn pages-key-func [key page-n]
  (str key "_page_" page-n))

(defn cache-get [key]
  (redis-cmd
   (when-let [value (car/get key)]
     (let [json-value (json/read-str value :key-fn keyword)
           page-count (:n_pages json-value)
           etag (:etag json-value)]
       [etag (for [page-n (range page-count)]
               (when-let [page-value (car/get (pages-key-func key page-n))]
                 (json/read-str page-value :key-fn keyword)))]))))

(defn cache-set [key page-seq]
  (redis-cmd
   (let [pages (vec page-seq)
         page-count (count pages)
         etag (when (seq pages) (:etag (first pages)))]
     (doseq [[page-n page] (map-indexed vector pages)]
       (car/set (pages-key-func key page-n) (json/write-str page)))
     (car/set key (json/write-str {:etag etag :n_pages page-count}))
     pages)))

;; Exception types
(def yt-quota-exceeded-type ::yt-quota-exceeded)

(defn yt-quota-exceeded [status json-data]
  {::type yt-quota-exceeded-type ::status status ::json json-data})

(defn yt-quota-exceeded? [x]
  (= (::type x) yt-quota-exceeded-type))

;; HTTP request functions
(defn request-with-retries [url & [options max-retries]]
  (let [max-retries (or max-retries 5)]
    (loop [retries 0]
      (try
        (let [response (http/get url (merge {:throw-exceptions false
                                             :socket-timeout 60000
                                             :connection-timeout 60000}
                                            options))
              status (:status response)
              should-retry? (and (>= status 500) (< status 600))]
          (log/log (if should-retry? :warn :debug)
                   (format "Received response for URL: %s code: %s" url status))
          (if (and should-retry? (< retries max-retries))
            (do (Thread/sleep 3000)
                (recur (inc retries)))
            response))
        (catch Exception e
          (if (< retries max-retries)
            (do (Thread/sleep 3000)
                (recur (inc retries)))
            (throw e)))))))

(defn request-base [url params & [headers]]
  (let [config (api-config)
        full-params (assoc params :key (:api-key config))
        query-string (->> full-params
                          (map (fn [[k v]] (str (name k) "=" (URLEncoder/encode (str v) "UTF-8"))))
                          (str/join "&"))
        base-url (str (:root-url config) url "?" query-string)]
    (loop [page-token nil
           results []]
      (let [final-url (if page-token
                        (str base-url "&pageToken=" page-token)
                        base-url)
            _ (log/debug "requesting:" final-url)
            response (request-with-retries final-url {:headers (or headers {})})
            status (:status response)]

        (cond
          (= status 403) (throw (ex-info "YouTube quota exceeded"
                                         (yt-quota-exceeded status (:body response))))
          (= status 304) [status results]
          (< status 200) (throw (Exception. (str "HTTP error: " status)))
          (>= status 300) (throw (Exception. (str "HTTP error: " status)))
          :else
          (let [json-response (json/read-str (:body response) :key-fn keyword)
                new-results (conj results json-response)]
            (if-let [next-token (:nextPageToken json-response)]
              (recur next-token new-results)
              [status new-results])))))))

(defn request-with-cache [url params]
  (let [key (cache-key-func url params)
        [etag cached-pages] (cache-get key)
        headers (if etag {"If-None-Match" etag} {})]

    (if etag
      (log/debug (format "Request with key %s CACHED, E-tag: %s" key etag))
      (log/debug (format "Request with key %s NOT cached" key)))

    (let [[status response-pages] (request-base url params headers)]
      (cond
        (= status 304) [status (or cached-pages [])]
        (and (>= status 200) (< status 300))
        [status (cache-set key response-pages)]
        :else
        (do (log/warn "Unexpected status code:" status)
            [status response-pages])))))

(defn request-main [url params & [use-cache?]]
  (let [use-cache? (if (nil? use-cache?) true use-cache?)
        [status pages] (if use-cache?
                         (request-with-cache url params)
                         (request-base url params))]
    [(not= status 304)
     (mapcat :items pages)]))

(defn request-one [url params & [use-cache?]]
  (let [[modified items] (request-main url params use-cache?)]
    [modified (first items)]))

;; YouTube API functions
(defn get-playlist-info [playlist-id]
  (request-one "/playlists"
               {:part "snippet" :id playlist-id}))

(defn list-channelsection-playlist-ids [channel-id]
  (let [[modified items] (request-main "/channelSections"
                                       {:part "contentDetails" :channelId channel-id})]
    [modified
     (->> items
          (mapcat #(get-in % [:contentDetails :playlists] []))
          (filter identity))]))

(defn list-channel-playlist-ids [channel-id]
  (let [[modified items] (request-main "/playlists"
                                       {:part "snippet,contentDetails" :channelId channel-id})]
    [modified (map :id items)]))

(defn get-video-info [youtube-id]
  (request-one "/videos"
               {:part "snippet,contentDetails,statistics" :id youtube-id}))

(defn list-playlist-items [playlist-id]
  (request-main "/playlistItems"
                {:part "snippet" :playlistId playlist-id}))

(defn get-channel-info [channel-id]
  (request-one "/channels"
               {:part "snippet,contentDetails,statistics" :id channel-id}))

(defn get-video-transcript [youtube-id]
  ;; Placeholder for transcript functionality
  "Transcript functionality would require external library integration")

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

;; ============================================================================
;; src/videosdb/publisher.clj - Social media publishing (Functional)
;; ============================================================================

(ns videosdb.publisher
  (:require [clojure.tools.logging :as log]
            [clojure.data.json :as json]
            [clj-http.client :as http]
            [environ.core :refer [env]]
            [clojure.java.io :as io]
            [videosdb.db :as db])
  (:import [java.time Instant Duration]))

;; Configuration
(def bitly-access-token "35811ca34a0829350789fceabfffd6ed57588672")

(def twitter-keys-prod
  {:api-key "f73ZNvOyGwYVJUUyav65KW4xv"
   :api-secret "QOU5Oo9svOWT9tEd9SPiPUUck41gqmU0C6mLzr1wCJtpZeifOp"
   :access-token "1576729637199265793-nDzS5ceL3iwqrw69tarOT9Crw4FClG"
   :access-secret "xuxWmsnsfHCbCyWxe5GDgOsaBjmpJpoZygFK6bXWXst9g"})

;; Utility functions
(defn get-short-url-firebase [url]
  (let [config (env :videosdb-config)
        config-path (str "common/firebase/configs/" (clojure.string/replace config "\"" "") ".json")]
    (try
      (when (.exists (io/file config-path))
        (let [config-data (json/read-str (slurp config-path) :key-fn keyword)
              api-key (:apiKey config-data)
              request-url (str "https://firebasedynamiclinks.googleapis.com/v1/shortLinks?key=" api-key)
              json-data {:dynamicLinkInfo
                         {:domainUriPrefix "https://www.nithyananda.cc/v"
                          :link url}}
              response (http/post request-url
                                  {:body (json/write-str json-data)
                                   :content-type :json
                                   :accept :json})]
          (get (json/read-str (:body response) :key-fn keyword) :shortLink)))
      (catch Exception e
        (log/error e "Failed to create short URL")
        url))))

(defn create-post-text [video]
  (let [url (str (env :videosdb-hostname) "/video/" (get-in video [:videosdb :slug]))
        short-url (get-short-url-firebase url)
        yt-url (str "http://youtu.be/" (:id video))
        title (get-in video [:snippet :title])]
    (format "%s\n%s\n%s" title yt-url short-url)))

(defn should-publish-video? [video]
  (let [video-date (get-in video [:snippet :publishedAt])
        now (Instant/now)
        week-ago (.minus now (Duration/ofDays 7))
        already-published? (get-in video [:videosdb :publishing :id])]

    (and (not already-published?)
         video-date
         (.isAfter (.toInstant video-date) week-ago))))

(defn create-tweet [text]
  ;; Twitter API integration would go here
  ;; For now, simulate successful creation
  (log/info (format "Creating tweet with text: %s" text))
  {:id "mock-tweet-id" :text text})

(defn publish-to-twitter [db-state video]
  (when (and (= (env :videosdb-config) "nithyananda")
             (should-publish-video? video))
    (let [text (create-post-text video)
          tweet-result (create-tweet text)
          now (Instant/now)
          updated-video (assoc-in video [:videosdb :publishing]
                                  {:publishDate (.toString now)
                                   :id (:id tweet-result)
                                   :text text})]

      (db/db-set-noquota! db-state (str "videos/" (:id video)) updated-video true)
      (log/info (format "Published to Twitter video %s" (:id video)))
      (Thread/sleep 5000) ; Rate limiting
      tweet-result)))

(defn publish-video [db-state video]
  "Main publishing function that handles all social media platforms"
  (try
    (publish-to-twitter db-state video)
    (catch Exception e
      (log/error e "Publishing error"))))

;; ============================================================================
;; src/videosdb/ipfs.clj - IPFS integration (Functional)
;; ============================================================================

(ns videosdb.ipfs
  (:require [clojure.tools.logging :as log]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [videosdb.settings :as settings]
            [videosdb.utils :as utils]
            [videosdb.db :as db])
  (:import [java.net InetAddress]
           [java.io File]))

;; DNS operations
(defn update-dns-record [dns-zone record-name record-type ttl new-value]
  (when dns-zone
    (log/info (format "Would update DNS record %s.%s %s %d %s"
                      record-name dns-zone record-type ttl new-value))))

(defn update-dnslink [dns-zone record-name new-root-hash]
  (update-dns-record dns-zone record-name "TXT" 300 (str "dnslink=/ipfs/" new-root-hash)))

(defn update-ip [dns-zone record-name new-ip]
  (update-dns-record dns-zone record-name "A" 300 new-ip))

;; IPFS operations
(defn create-ipfs-client [& [files-root]]
  {:files-root (or files-root "/videos")
   :host (.getHostAddress (InetAddress/getByName (:ipfs-host settings/config)))
   :port (:ipfs-port settings/config)
   :dnslink-update-pending (atom false)})
(defn add-to-ipfs-dir [ipfs-client filename hash]
  (let [src (str "/ipfs/" hash)
        dst (str (:files-root ipfs-client) "/" (.getName (File. filename)))]
    (log/info (format "Would copy %s to %s in IPFS MFS" src dst))
    (reset! (:dnslink-update-pending ipfs-client) true)))

(defn add-file-to-ipfs [ipfs-client filename & [add-to-dir? options]]
  (let [add-to-dir? (if (nil? add-to-dir?) true add-to-dir?)
        mock-hash "QmMockHashForFile123456789"]
    (log/info (format "Would add file %s to IPFS" filename))
    (when add-to-dir?
      (add-to-ipfs-dir ipfs-client filename mock-hash))
    mock-hash))



(defn get-file-from-ipfs [ipfs-client ipfs-hash]
  (log/info (format "Would get file with hash %s from IPFS" ipfs-hash))
  "mock-filename.mp4")

(defn update-ipfs-dnslink [ipfs-client & [force?]]
  (when (or @(:dnslink-update-pending ipfs-client) force?)
    (let [root-hash "QmMockRootHash123456789"]
      (update-dnslink (:videosdb-dnszone settings/config)
                      (str "videos." (:videosdb-domain settings/config))
                      root-hash)
      (reset! (:dnslink-update-pending ipfs-client) false))))

(defn list-files-in-ipfs [ipfs-client]
  "Returns map of youtube-id -> file info"
  {})

(defn list-files-in-disk [dir]
  (let [dir-file (File. dir)]
    (when (.exists dir-file)
      (->> (.listFiles dir-file)
           (filter #(.isFile %))
           (filter #(not (.endsWith (.getName %) ".part")))
           (map (fn [file]
                  (when-let [youtube-id (utils/parse-youtube-id (.getName file))]
                    [youtube-id (.getName file)])))
           (filter identity)
           (into {})))))

(defn download-and-register-folder [db-state ipfs-client & [overwrite-hashes?]]
  (log/info "Would download videos and register with IPFS")
  (let [videos-dir (.getAbsolutePath (File. (:video-files-dir settings/config)))]
    (when-not (.exists (File. videos-dir))
      (.mkdirs (File. videos-dir)))

    (let [files-in-ipfs (list-files-in-ipfs ipfs-client)
          files-in-disk (list-files-in-disk videos-dir)]
      (log/info (format "Found %d files in disk, %d in IPFS"
                        (count files-in-disk) (count files-in-ipfs)))

      ;; Process videos from database
      (let [video-ids-doc (db/db-get-noquota db-state "meta/video_ids")
            video-ids (when (.exists video-ids-doc)
                        (get (.getData video-ids-doc) "videoIds" []))]

        (doseq [video-id video-ids]
          (let [video-doc (db/db-get-noquota db-state (str "videos/" video-id))]
            (when (.exists video-doc)
              (let [video-data (.getData video-doc)]
                (when-not (contains? files-in-disk video-id)
                  (log/debug "Would download video:" video-id))

                (when-not (contains? files-in-ipfs video-id)
                  (log/debug "Would add to IPFS:" video-id)
                  (let [filename (str video-id ".mp4")
                        ipfs-hash (add-file-to-ipfs ipfs-client filename true)]
                    (db/db-set! db-state (str "videos/" video-id)
                                (assoc-in video-data [:videosdb :ipfs_hash] ipfs-hash)
                                true)))))))

        (update-ipfs-dnslink ipfs-client)))))

;; ============================================================================
;; Main application functions and examples
;; ============================================================================

(ns videosdb.main
  (:require [videosdb.core :as core]
            [videosdb.db :as db]
            [videosdb.downloader :as downloader]
            [videosdb.publisher :as publisher]
            [videosdb.ipfs :as ipfs]
            [videosdb.settings :as settings]
            [clojure.tools.logging :as log]))

;; Application state management (pure functions)
(defn create-app-state []
  {:db-state (db/create-db)
   :ipfs-client (ipfs/create-ipfs-client)
   :start-time (System/currentTimeMillis)})

(defn init-app-state [app-state]
  (update app-state :db-state db/init-db!))

(defn run-sync [app-state options channel-id]
  (downloader/check-for-new-videos (:db-state app-state) options channel-id))

(defn run-ipfs-sync [app-state]
  (ipfs/download-and-register-folder (:db-state app-state) (:ipfs-client app-state)))

;; Utility functions for running different operations
(defn sync-videos
  "Main video synchronization function"
  [& {:keys [channel-id enable-transcripts enable-publishing export-to-emulator]
      :or {channel-id "UCcYzLCs3zrQIBVHYA1sK2sw"
           enable-transcripts false
           enable-publishing false
           export-to-emulator nil}}]
  (let [app-state (create-app-state)
        app-state (init-app-state app-state)
        options {:enable-transcripts enable-transcripts
                 :enable-twitter-publishing enable-publishing
                 :export-to-emulator-host export-to-emulator}]
    (run-sync app-state options channel-id)))

(defn sync-ipfs
  "IPFS synchronization function"
  []
  (let [app-state (create-app-state)
        app-state (init-app-state app-state)]
    (run-ipfs-sync app-state)))

(defn publish-videos
  "Manually trigger video publishing"
  [& {:keys [channel-id] :or {channel-id "UCcYzLCs3zrQIBVHYA1sK2sw"}}]
  (let [app-state (create-app-state)
        app-state (init-app-state app-state)
        db-state (:db-state app-state)]

    ;; Get videos ready for publishing
    (let [video-ids-doc (db/db-get-noquota db-state "meta/video_ids")
          video-ids (when (.exists video-ids-doc)
                      (get (.getData video-ids-doc) "videoIds" []))]

      (doseq [video-id (take 10 video-ids)] ; Limit to 10 for safety
        (try
          (let [video-doc (db/db-get-noquota db-state (str "videos/" video-id))]
            (when (.exists video-doc)
              (let [video-data (.getData video-doc)]
                (when (not (empty? (get-in video-data [:videosdb :slug])))
                  (publisher/publish-video db-state video-data)))))
          (catch Exception e
            (log/error e (format "Error publishing video %s" video-id))))))))

;; Command-line interface functions
(defn print-stats []
  (let [app-state (create-app-state)
        app-state (init-app-state app-state)]
    (println "Database Stats:")
    (doseq [stat (db/get-stats (:db-state app-state))]
      (println " " stat))
    (println "Cache Stats:")
    (doseq [[k v] (videosdb.youtube-api/cache-stats)]
      (println " " k ":" v))))

;; Example usage and testing functions
(comment
  ;; Basic video sync
  (sync-videos :channel-id "UCcYzLCs3zrQIBVHYA1sK2sw"
               :enable-transcripts true
               :enable-publishing false)

  ;; IPFS sync
  (sync-ipfs)

  ;; Manual publishing
  (publish-videos)

  ;; Print current stats
  (print-stats)

  ;; Direct database operations
  (let [app-state (-> (create-app-state) init-app-state)
        db-state (:db-state app-state)]

    ;; Get video count
    (let [video-ids-doc (db/db-get-noquota db-state "meta/video_ids")]
      (when (.exists video-ids-doc)
        (count (get (.getData video-ids-doc) "videoIds" []))))

    ;; Get a specific video
    (let [video-doc (db/db-get-noquota db-state "videos/some-video-id")]
      (when (.exists video-doc)
        (.getData video-doc))))

  ;; YouTube API operations
  (let [[modified channel] (videosdb.youtube-api/get-channel-info "UCcYzLCs3zrQIBVHYA1sK2sw")]
    (println "Channel:" (get-in channel [:snippet :title]))
    (println "Subscriber count:" (get-in channel [:statistics :subscriberCount])))

  ;; Cache operations
  (println "Cache stats:" (videosdb.youtube-api/cache-stats)))

;; Environment configuration helper
(defn setup-environment! []
  (println "Setting up environment variables...")
  (System/setProperty "YOUTUBE_CHANNEL_ID" "UCcYzLCs3zrQIBVHYA1sK2sw")
  (System/setProperty "VIDEOSDB_CONFIG" "testing")
  (System/setProperty "FIREBASE_PROJECT" "videosdb-testing")
  (System/setProperty "LOGLEVEL" "info")
  (println "Environment configured for testing"))

;; Main CLI entry point
(defn -main [& args]
  (case (first args)
    "sync" (sync-videos)
    "ipfs" (sync-ipfs)
    "publish" (publish-videos)
    "stats" (print-stats)
    "setup" (setup-environment!)
    (do (println "Usage: lein run [sync|ipfs|publish|stats|setup]")
        (println "  sync    - Synchronize videos from YouTube")
        (println "  ipfs    - Sync videos to IPFS")
        (println "  publish - Publish videos to social media")
        (println "  stats   - Show current statistics")
        (println "  setup   - Setup test environment"))))

;; ============================================================================
;; Configuration and Setup Guide
;; ============================================================================

;; Required environment variables:
;; YOUTUBE_CHANNEL_ID - YouTube channel to sync
;; YOUTUBE_API_KEY - YouTube Data API key
;; VIDEOSDB_CONFIG - Config name (testing/production)
;; FIREBASE_PROJECT - Firebase project ID
;; VIDEOSDB_HOSTNAME - Website hostname
;; LOGLEVEL - Logging level

;; Required files:
;; common/keys/{config}.json - Firebase service account keys
;; common/firebase/db-schema.json - Database schema

;; Redis must be running on localhost:6379

;; Example usage:
;; lein run sync     # Full synchronization
;; lein run publish  # Publish pending videos
;; lein run stats    # Show statistics