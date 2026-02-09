(ns videosdb.youtube-api
  "YouTube Data API v3 client. Replaces youtube_api.py."
  (:require [hato.client :as hc]
            [clojure.data.json :as json]
            [clojure.tools.logging :as log]
            [clojure.string :as str]
            [videosdb.config :as config]
            [videosdb.cache :as cache])
  (:import [java.net URLEncoder]))

;; --- Exceptions ---

(defn quota-exceeded? [e]
  (= :yt-quota-exceeded (:type (ex-data e))))

;; --- HTTP with retries ---

(defn- get-with-retries
  "HTTP GET with retry on 5xx errors. Up to max-retries with 3s backoff."
  [http-client url & {:keys [headers timeout max-retries]
                      :or   {timeout 60000 max-retries 5}}]
  (loop [retries 0]
    (let [resp (hc/get url {:http-client http-client
                            :headers     (or headers {})
                            :timeout     timeout
                            :as          :string})]
      (if (and (>= (:status resp) 500) (< (:status resp) 600))
        (do
          (log/warn "5xx response for" url "status:" (:status resp))
          (if (> retries max-retries)
            (throw (ex-info "Max retries exceeded"
                            {:url url :status (:status resp)}))
            (do
              (Thread/sleep 3000)
              (recur (inc retries)))))
        resp))))

;; --- Core API ---

(defn make-client
  "Create a YouTube API client map."
  ([] (make-client {}))
  ([{:keys [yt-key redis-db-n]}]
   (let [api-key  (or yt-key
                      (config/env "YOUTUBE_API_KEY")
                      "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU")
         root-url (config/env "YOUTUBE_API_URL"
                              "https://www.googleapis.com/youtube/v3")]
     (log/debug "YouTube API pointing at:" root-url)
     {:http-client (hc/build-http-client {:connect-timeout 10000
                                          :redirect-policy :normal})
      :api-key     api-key
      :root-url    root-url
      :cache-opts  (cache/make-conn-opts redis-db-n)})))

(defn- request-base
  "Raw paginated HTTP request. Returns vector of [status-code & pages]."
  [{:keys [http-client api-key root-url]} url params & [headers]]
  (let [full-params (assoc params "key" api-key)
        query-str   (str/join "&" (map (fn [[k v]] (str (name k) "=" (URLEncoder/encode (str v) "UTF-8")))
                                       full-params))
        base-url    (str url "?" query-str)]
    (loop [page-token nil
           result     []]
      (let [final-url (str root-url
                           (if page-token
                             (str base-url "&pageToken=" page-token)
                             base-url))
            resp      (get-with-retries http-client final-url
                                        :headers (or headers {}))]

        (when (= 403 (:status resp))
          (throw (ex-info "YouTube API quota exceeded"
                          {:type :yt-quota-exceeded
                           :status 403
                           :body (:body resp)})))

        (when (and (not= 304 (:status resp))
                   (>= (:status resp) 300))
          (throw (ex-info "YouTube API error"
                          {:status (:status resp)
                           :body   (:body resp)})))

        (if (= 304 (:status resp))
          ;; Not modified - return status only on first page
          (if (empty? result)
            [304]
            result)
          (let [body      (if (string? (:body resp))
                            (json/read-str (:body resp) :key-fn keyword)
                            (:body resp))
                new-result (if (empty? result)
                             (conj result (:status resp) body)
                             (conj result body))
                next-token (:nextPageToken body)]
            (if next-token
              (recur next-token new-result)
              new-result)))))))

(defn- request-with-cache
  "Cached request using ETags. Returns [status-code & pages]."
  [client url params]
  (let [cache-key       (cache/key-func url params)
        [etag cached]   (cache/cache-get (:cache-opts client) cache-key)
        headers         (when etag {"If-None-Match" etag})
        _               (if etag
                          (log/debug "Request" cache-key "CACHED, ETag:" etag)
                          (log/debug "Request" cache-key "NOT cached"))
        raw-result      (request-base client url params headers)
        status-code     (first raw-result)]

    (cond
      (= status-code 304)
      (do
        (log/debug "304 Not Modified, using cache")
        (into [304] cached))

      (and (>= status-code 200) (< status-code 300))
      (let [pages (rest raw-result)
            stored (cache/cache-set (:cache-opts client) cache-key (vec pages))]
        (into [status-code] stored))

      :else
      (do
        (log/warn "Unexpected status code:" status-code)
        raw-result))))

(defn- request-main
  "Main request returning [modified? items-seq]."
  ([client url params] (request-main client url params true))
  ([client url params use-cache?]
   (let [raw (if use-cache?
               (request-with-cache client url params)
               (request-base client url params))
         status-code (first raw)
         pages       (rest raw)
         items       (mapcat :items pages)]
     [(not= status-code 304) items])))

(defn- request-one
  "Request returning [modified? single-item-or-nil]."
  ([client url params] (request-one client url params true))
  ([client url params use-cache?]
   (let [[modified? items] (request-main client url params use-cache?)]
     [modified? (first items)])))

;; --- Public API methods ---

(defn get-channel-info
  "Get channel info by ID."
  [client channel-id]
  (request-one client "/channels"
               {"part" "snippet,contentDetails,statistics"
                "id"   channel-id}))

(defn list-channelsection-playlist-ids
  "List playlist IDs from channel sections."
  [client channel-id]
  (let [[modified? items] (request-main client "/channelSections"
                                        {"part"      "contentDetails"
                                         "channelId" channel-id})]
    [modified?
     (->> items
          (mapcat (fn [item]
                    (get-in item [:contentDetails :playlists] [])))
          distinct)]))

(defn list-channel-playlist-ids
  "List all playlist IDs for a channel."
  [client channel-id]
  (let [[modified? items] (request-main client "/playlists"
                                        {"part"      "snippet,contentDetails"
                                         "channelId" channel-id})]
    [modified? (map :id items)]))

(defn get-playlist-info
  "Get info for a single playlist."
  [client playlist-id]
  (request-one client "/playlists"
               {"part" "snippet"
                "id"   playlist-id}))

(defn list-playlist-items
  "List all items in a playlist."
  [client playlist-id]
  (request-main client "/playlistItems"
                {"part"       "snippet"
                 "playlistId" playlist-id}))

(defn get-video-info
  "Get info for a single video."
  [client youtube-id]
  (request-one client "/videos"
               {"part" "snippet,contentDetails,statistics"
                "id"   youtube-id}))
