
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
