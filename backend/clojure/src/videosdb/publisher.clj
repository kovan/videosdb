

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
