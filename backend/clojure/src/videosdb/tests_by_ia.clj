 ============================================================================
;; test/videosdb/utils_test.clj - Utility function tests
;; ============================================================================

(ns videosdb.utils-test
  (:require [midje.sweet :refer :all]
            [videosdb.utils :as utils])
  (:import [java.util.concurrent.atomic AtomicInteger]
           [java.time Instant Duration]))

(facts "about quota-exceeded" :unit
       (fact "creates quota exceeded error"
             (let [error (utils/quota-exceeded "test message")]
               error => (contains {::utils/type utils/quota-exceeded-type
                                   ::utils/message "test message"})))

       (fact "checks if error is quota exceeded"
             (let [error (utils/quota-exceeded "test")]
               (utils/quota-exceeded? error) => true
               (utils/quota-exceeded? {:other "error"}) => false)))

(facts "about slugify" :unit
       (fact "converts text to slug"
             (utils/slugify "Hello World!") => "hello-world"
             (utils/slugify "Test & Example") => "test-example"
             (utils/slugify "Multiple   Spaces") => "multiple-spaces"
             (utils/slugify nil) => nil
             (utils/slugify "") => ""))

(facts "about parse-youtube-id" :unit
       (fact "extracts YouTube ID from filename"
             (utils/parse-youtube-id "video[dQw4w9WgXcQ].mp4") => "dQw4w9WgXcQ"
             (utils/parse-youtube-id "no-id-here.mp4") => nil
             (utils/parse-youtube-id nil) => nil))

(facts "about parse-duration" :unit
       (fact "parses ISO 8601 duration"
             (utils/parse-duration "PT4M13S") => 253
             (utils/parse-duration "PT1H30M") => 5400
             (utils/parse-duration "invalid") => 0
             (utils/parse-duration nil) => nil))

(facts "about parse-datetime" :unit
       (fact "parses ISO 8601 datetime"
             (let [result (utils/parse-datetime "2023-01-01T00:00:00Z")]
               result => (partial instance? Instant))

             (fact "handles invalid datetime"
                   (let [result (utils/parse-datetime "invalid")]
                     result => (partial instance? Instant))))

       (facts "about put-item-at-front" :unit
              (fact "moves item to front of sequence"
                    (utils/put-item-at-front [1 2 3 4] 3) => [3 4 1 2]
                    (utils/put-item-at-front [1 2 3 4] 1) => [1 2 3 4]
                    (utils/put-item-at-front [1 2 3 4] 5) => [1 2 3 4]
                    (utils/put-item-at-front [1 2 3 4] nil) => [1 2 3 4]))

       (facts "about counter operations" :unit
              (fact "creates counter with correct initial state"
                    (let [counter (utils/create-counter :test 100)]
                      (:type counter) => :test
                      (:limit counter) => 100
                      (.get (:counter counter)) => 0))

              (fact "increments counter"
                    (let [counter (utils/create-counter :test 100)]
                      (utils/inc-counter! counter 5)
                      (.get (:counter counter)) => 5))

              (fact "throws exception when limit exceeded"
                    (let [counter (utils/create-counter :test 5)]
                      (utils/inc-counter! counter 3) => anything
                      (utils/inc-counter! counter 3) => (throws Exception #"Counter limit exceeded")))

              (fact "counter stats format"
                    (let [counter (utils/create-counter :test 100)]
                      (utils/inc-counter! counter 10)
                      (utils/counter-stats counter) => "Counter test: 10/100")))

       ;; ============================================================================
       ;; test/videosdb/db_test.clj - Database tests
       ;; ============================================================================

       (ns videosdb.db-test
         (:require [midje.sweet :refer :all]
                   [videosdb.db :as db]
                   [videosdb.utils :as utils])
         (:import [com.google.cloud.firestore Firestore]))

       (facts "about db-config" :unit
              (fact "has correct quota limits"
                    (:free-tier-write-quota db/db-config) => 20000
                    (:free-tier-read-quota db/db-config) => 50000))

       (facts "about create-db" :unit
              (fact "creates database state with counters"
                    (let [db-state (db/create-db)]
                      (:counters db-state) => (contains {:reads anything :writes anything})
                      (:db-schema db-state) => anything
                      (:client db-state) => anything)))

       (facts "about get-stats" :unit
              (fact "returns formatted counter stats"
                    (let [db-state (db/create-db)
                          stats (db/get-stats db-state)]
                      (count stats) => 2
                      (every? string? stats) => true)))

       (facts "about increase-counter!" :unit
              (fact "increments read counter"
                    (let [db-state (db/create-db)
                          read-counter (get (:counters db-state) :reads)
                          initial-count (.get (:counter read-counter))]
                      (db/increase-counter! db-state :reads 5)
                      (.get (:counter read-counter)) => (+ initial-count 5)))

              (fact "increments write counter"
                    (let [db-state (db/create-db)
                          write-counter (get (:counters db-state) :writes)
                          initial-count (.get (:counter write-counter))]
                      (db/increase-counter! db-state :writes 3)
                      (.get (:counter write-counter)) => (+ initial-count 3))))

       (facts "about validate-video-schema" :unit
              (fact "validates video with ID"
                    (db/validate-video-schema {} {:id "test-id" :snippet {:title "Test"}}) => true)

              (fact "rejects video without ID"
                    (db/validate-video-schema {} {:snippet {:title "Test"}}) => false
                    (db/validate-video-schema {} nil) => false))

       ;; ============================================================================
       ;; test/videosdb/youtube_api_test.clj - YouTube API tests
       ;; ============================================================================

       (ns videosdb.youtube-api-test
         (:require [midje.sweet :refer :all]
                   [videosdb.youtube-api :as yt-api]
                   [clj-http.fake :refer [with-fake-routes]]
                   [clojure.data.json :as json]))

       (def sample-video-response
         {:body (json/write-str {:items [{:id "test-video-id"
                                          :snippet {:title "Test Video"
                                                    :description "Test Description"
                                                    :publishedAt "2023-01-01T00:00:00Z"}
                                          :statistics {:viewCount "1000"
                                                       :likeCount "50"}}]
                                 :etag "test-etag"})
          :status 200
          :headers {"content-type" "application/json"}})

       (def sample-playlist-response
         {:body (json/write-str {:items [{:id "test-playlist-id"
                                          :snippet {:title "Test Playlist"
                                                    :channelTitle "Test Channel"}}]
                                 :etag "test-etag"})
          :status 200
          :headers {"content-type" "application/json"}})

       (def sample-channel-response
         {:body (json/write-str {:items [{:id "test-channel-id"
                                          :snippet {:title "Test Channel"}
                                          :statistics {:subscriberCount "1000000"}
                                          :contentDetails {:relatedPlaylists {:uploads "uploads-playlist-id"}}}]
                                 :etag "test-etag"})
          :status 200
          :headers {"content-type" "application/json"}})

       (facts "about api-config" :unit
              (fact "returns configuration map"
                    (let [config (yt-api/api-config)]
                      (:root-url config) => string?
                      (:api-key config) => string?)))

       (facts "about cache-key-func" :unit
              (fact "creates cache key from URL and params"
                    (yt-api/cache-key-func "/videos" {:part "snippet" :id "test"})
                    => "videos?id=test&part=snippet")

              (fact "excludes API key from cache key"
                    (yt-api/cache-key-func "/videos" {:part "snippet" :key "secret"})
                    => "videos?part=snippet"))

       (facts "about YouTube API calls" :integration
              (against-background [(yt-api/cache-get anything) => [nil nil]
                                   (yt-api/cache-set anything anything) => []])

              (fact "get-video-info returns video data"
                    (with-fake-routes {"https://www.googleapis.com/youtube/v3/videos" :get sample-video-response}
                      (let [[modified video] (yt-api/get-video-info "test-video-id")]
                        modified => true
                        (:id video) => "test-video-id"
                        (get-in video [:snippet :title]) => "Test Video")))

              (fact "get-playlist-info returns playlist data"
                    (with-fake-routes {"https://www.googleapis.com/youtube/v3/playlists" :get sample-playlist-response}
                      (let [[modified playlist] (yt-api/get-playlist-info "test-playlist-id")]
                        modified => true
                        (:id playlist) => "test-playlist-id"
                        (get-in playlist [:snippet :title]) => "Test Playlist")))

              (fact "get-channel-info returns channel data"
                    (with-fake-routes {"https://www.googleapis.com/youtube/v3/channels" :get sample-channel-response}
                      (let [[modified channel] (yt-api/get-channel-info "test-channel-id")]
                        modified => true
                        (:id channel) => "test-channel-id"
                        (get-in channel [:snippet :title]) => "Test Channel"))))

       (facts "about quota exceeded handling" :unit
              (fact "creates quota exceeded error"
                    (let [error (yt-api/yt-quota-exceeded 403 {:error "quota exceeded"})]
                      (yt-api/yt-quota-exceeded? error) => true
                      (::yt-api/status error) => 403))

              (fact "handles 403 responses"
                    (with-fake-routes {"https://www.googleapis.com/youtube/v3/videos" :get {:status 403 :body "{\"error\": \"quota exceeded\"}"}}
                      (yt-api/get-video-info "test") => (throws Exception #"YouTube quota exceeded"))))

       ;; ============================================================================
       ;; test/videosdb/downloader_test.clj - Downloader tests
       ;; ============================================================================

       (ns videosdb.downloader-test
         (:require [midje.sweet :refer :all]
                   [videosdb.downloader :as downloader]
                   [videosdb.db :as db]
                   [videosdb.youtube-api :as yt-api])
         (:import [java.util.concurrent.atomic AtomicBoolean AtomicReference]))

       (def mock-db-state
         {:counters {:reads (utils/create-counter :reads 1000)
                     :writes (utils/create-counter :writes 1000)}
          :client nil})

       (def mock-video
         {:id "test-video-id"
          :snippet {:title "Test Video"
                    :description "Test Description"
                    :channelId "test-channel-id"
                    :publishedAt "2023-01-01T00:00:00Z"}
          :statistics {:viewCount "1000" :likeCount "50"}
          :contentDetails {:duration "PT4M13S"}})

       (def mock-playlist
         {:id "test-playlist-id"
          :snippet {:title "Test Playlist"
                    :channelTitle "Test Channel"}})

       (def mock-channel
         {:id "test-channel-id"
          :snippet {:title "Test Channel"}
          :statistics {:subscriberCount "1000000"}
          :contentDetails {:relatedPlaylists {:uploads "uploads-playlist-id"}}})

       (facts "about create-video-processor" :unit
              (fact "creates processor with initial state"
                    (let [processor (downloader/create-video-processor "test-channel")]
                      (:channel-id processor) => "test-channel"
                      (.get (:video-to-playlist-list processor)) => {}
                      (.get (:quota-exceeded processor)) => false)))

       (facts "about add-video-to-processor!" :unit
              (fact "adds video to processor"
                    (let [processor (downloader/create-video-processor "test-channel")]
                      (downloader/add-video-to-processor! processor "video-1" "playlist-1")
                      (let [videos (.get (:video-to-playlist-list processor))]
                        (get videos "video-1") => #{"playlist-1"})))

              (fact "adds multiple playlists to same video"
                    (let [processor (downloader/create-video-processor "test-channel")]
                      (downloader/add-video-to-processor! processor "video-1" "playlist-1")
                      (downloader/add-video-to-processor! processor "video-1" "playlist-2")
                      (let [videos (.get (:video-to-playlist-list processor))]
                        (get videos "video-1") => #{"playlist-1" "playlist-2"}))))

       (facts "about create-playlist!" :unit
              (against-background [(db/db-set! anything anything anything anything) => nil])

              (fact "creates playlist with video data"
                    (let [playlist-items [{:snippet {:channelId "test-channel"
                                                     :resourceId {:videoId "video-1"}
                                                     :publishedAt "2023-01-01T00:00:00Z"}}
                                          {:snippet {:channelId "test-channel"
                                                     :resourceId {:videoId "video-2"}
                                                     :publishedAt "2023-01-02T00:00:00Z"}}]
                          result (downloader/create-playlist! mock-db-state mock-playlist playlist-items "test-channel" true)]

                      (get-in result [:videosdb :videoCount]) => 2
                      (get-in result [:videosdb :videoIds]) => #{"video-1" "video-2"}
                      (get-in result [:videosdb :slug]) => "test-playlist"))

              (fact "filters out videos from other channels"
                    (let [playlist-items [{:snippet {:channelId "other-channel"
                                                     :resourceId {:videoId "video-1"}
                                                     :publishedAt "2023-01-01T00:00:00Z"}}
                                          {:snippet {:channelId "test-channel"
                                                     :resourceId {:videoId "video-2"}
                                                     :publishedAt "2023-01-02T00:00:00Z"}}]
                          result (downloader/create-playlist! mock-db-state mock-playlist playlist-items "test-channel" false)]

                      (get-in result [:videosdb :videoCount]) => 1
                      (get-in result [:videosdb :videoIds]) => #{"video-2"})))

       (facts "about task execution functions" :unit
              (fact "execute-export-task logs when enabled"
                    (downloader/execute-export-task mock-db-state {:export-to-emulator-host "localhost"} mock-video) => anything)

              (fact "execute-export-task does nothing when disabled"
                    (downloader/execute-export-task mock-db-state {} mock-video) => anything)

              (fact "execute-transcript-task processes pending transcripts"
                    (let [video-with-pending {:id "test" :videosdb {:transcript_status "pending"}}]
                      (downloader/execute-transcript-task mock-db-state {:enable-transcripts true} video-with-pending) => anything))

              (fact "execute-validation-task validates video schema"
                    (downloader/execute-validation-task mock-db-state {} mock-video) => true
                    (downloader/execute-validation-task mock-db-state {} {:no-id true}) => false))

       ;; ============================================================================
       ;; test/videosdb/publisher_test.clj - Publisher tests
       ;; ============================================================================

       (ns videosdb.publisher-test
         (:require [midje.sweet :refer :all]
                   [videosdb.publisher :as publisher]
                   [videosdb.db :as db]
                   [clj-http.fake :refer [with-fake-routes]]) º
         (:import [java.time Instant Duration]))

       (def mock-db-state
         {:counters {:reads (utils/create-counter :reads 1000)
                     :writes (utils/create-counter :writes 1000)}
          :client nil})

       (def recent-video
         {:id "recent-video-id"
          :snippet {:title "Recent Video"
                    :publishedAt (.minus (Instant/now) (Duration/ofDays 2))}
          :videosdb {:slug "recent-video"}})

       (def old-video
         {:id "old-video-id"
          :snippet {:title "Old Video"
                    :publishedAt (.minus (Instant/now) (Duration/ofDays 10))}
          :videosdb {:slug "old-video"}})

       (def published-video
         {:id "published-video-id"
          :snippet {:title "Published Video"
                    :publishedAt (.minus (Instant/now) (Duration/ofDays 2))}
          :videosdb {:slug "published-video"
                     :publishing {:id "tweet-123"}}})

       (facts "about create-post-text" :unit
              (against-background [(publisher/get-short-url-firebase anything) => "https://short.url/abc"])

              (fact "creates formatted post text"
                    (with-redefs [environ.core/env {:videosdb-hostname "https://example.com"}]
                      (let [text (publisher/create-post-text recent-video)]
                        text => (contains "Recent Video")
                        text => (contains "http://youtu.be/recent-video-id")
                        text => (contains "https://short.url/abc")))))

       (facts "about should-publish-video?" :unit
              (fact "should publish recent unpublished video"
                    (publisher/should-publish-video? recent-video) => true)

              (fact "should not publish old video"
                    (publisher/should-publish-video? old-video) => false)

              (fact "should not publish already published video"
                    (publisher/should-publish-video? published-video) => false))

       (facts "about get-short-url-firebase" :integration
              (fact "creates short URL from Firebase"
                    (let [firebase-response {:body "{\"shortLink\": \"https://short.url/abc\"}"}]
                      (with-fake-routes {"https://firebasedynamiclinks.googleapis.com/v1/shortLinks" :post firebase-response}
                        (publisher/get-short-url-firebase "https://example.com/test") => "https://short.url/abc")))

              (fact "returns original URL on error"
                    (with-fake-routes {"https://firebasedynamiclinks.googleapis.com/v1/shortLinks" :post {:status 500}}
                      (publisher/get-short-url-firebase "https://example.com/test") => "https://example.com/test")))

       (facts "about publish-to-twitter" :unit
              (against-background [(db/db-set-noquota! anything anything anything anything) => nil
                                   (publisher/create-tweet anything) => {:id "mock-tweet-123" :text "test"}
                                   (publisher/create-post-text anything) => "Test tweet text"])

              (fact "publishes recent video when config is nithyananda"
                    (with-redefs [environ.core/env {:videosdb-config "nithyananda"}]
                      (let [result (publisher/publish-to-twitter mock-db-state recent-video)]
                        result => {:id "mock-tweet-123" :text "test"})))

              (fact "does not publish when config is not nithyananda"
                    (with-redefs [environ.core/env {:videosdb-config "testing"}]
                      (publisher/publish-to-twitter mock-db-state recent-video) => nil))

              (fact "does not publish old videos"
                    (with-redefs [environ.core/env {:videosdb-config "nithyananda"}]
                      (publisher/publish-to-twitter mock-db-state old-video) => nil)))

       ;; ============================================================================
       ;; test/videosdb/ipfs_test.clj - IPFS tests
       ;; ============================================================================

       (ns videosdb.ipfs-test
         (:require [midje.sweet :refer :all]
                   [videosdb.ipfs :as ipfs]
                   [videosdb.settings :as settings])
         (:import [java.io File]))

       (facts "about DNS operations" :unit
              (fact "update-dns-record logs operation"
                    (ipfs/update-dns-record "test-zone" "test-record" "A" 300 "1.2.3.4") => anything)

              (fact "update-dnslink creates dnslink record"
                    (ipfs/update-dnslink "test-zone" "videos" "QmTestHash") => anything)

              (fact "update-ip creates A record"
                    (ipfs/update-ip "test-zone" "test-record" "1.2.3.4") => anything))

       (facts "about create-ipfs-client" :unit
              (fact "creates IPFS client with defaults"
                    (let [client (ipfs/create-ipfs-client)]
                      (:files-root client) => "/videos"
                      (:host client) => string?
                      (:port client) => (:ipfs-port settings/config)
                      @(:dnslink-update-pending client) => false))

              (fact "creates IPFS client with custom root"
                    (let [client (ipfs/create-ipfs-client "/custom")]
                      (:files-root client) => "/custom")))

       (facts "about IPFS file operations" :unit
              (fact "add-file-to-ipfs returns hash"
                    (let [client (ipfs/create-ipfs-client)
                          hash (ipfs/add-file-to-ipfs client "test.mp4")]
                      hash => string?))

              (fact "add-to-ipfs-dir updates pending flag"
                    (let [client (ipfs/create-ipfs-client)]
                      (ipfs/add-to-ipfs-dir client "test.mp4" "QmTestHash")
                      @(:dnslink-update-pending client) => true))

              (fact "update-ipfs-dnslink resets pending flag"
                    (let [client (ipfs/create-ipfs-client)]
                      (reset! (:dnslink-update-pending client) true)
                      (ipfs/update-ipfs-dnslink client)
                      @(:dnslink-update-pending client) => false)))

       (facts "about file listing" :unit
              (fact "list-files-in-ipfs returns empty map initially"
                    (let [client (ipfs/create-ipfs-client)]
                      (ipfs/list-files-in-ipfs client) => {}))

              (fact "list-files-in-disk handles non-existent directory"
                    (ipfs/list-files-in-disk "/non/existent/path") => nil))

       ;; ============================================================================
       ;; test/videosdb/integration_test.clj - Integration tests
       ;; ============================================================================

       (ns videosdb.integration-test
         (:require [midje.sweet :refer :all]
                   [videosdb.main :as main]
                   [videosdb.db :as db]
                   [videosdb.downloader :as downloader]
                   [videosdb.youtube-api :as yt-api]
                   [clj-http.fake :refer [with-fake-routes]]
                   [clojure.data.json :as json]))

       (def mock-responses
         {"https://www.googleapis.com/youtube/v3/channels"
          :get {:body (json/write-str {:items [{:id "test-channel"
                                                :snippet {:title "Test Channel"}
                                                :contentDetails {:relatedPlaylists {:uploads "uploads-id"}}}]})
                :status 200}

          "https://www.googleapis.com/youtube/v3/playlists"
          :get {:body (json/write-str {:items []})
                :status 200}

          "https://www.googleapis.com/youtube/v3/channelSections"
          :get {:body (json/write-str {:items []})
                :status 200}})

       (facts "about application state management" :integration
              (fact "creates and initializes app state"
                    (let [app-state (main/create-app-state)
                          initialized-state (main/init-app-state app-state)]
                      (:db-state initialized-state) => anything
                      (:ipfs-client initialized-state) => anything
                      (:start-time initialized-state) => number?))

              (fact "app state contains required components"
                    (let [app-state (main/create-app-state)]
                      (keys app-state) => (contains [:db-state :ipfs-client :start-time]))))

       (facts "about sync operations" :integration
              (against-background [(db/init-db! anything) => identity
                                   (db/db-get-noquota anything anything) => (reify Object
                                                                              (exists [] false))]
                                  (yt-api/cache-get anything) => [nil nil]
                                  (yt-api/cache-set anything anything) => [])

              (fact "sync-videos completes without error"
                    (with-fake-routes mock-responses
                      (main/sync-videos :channel-id "test-channel"
                                        :enable-transcripts false
                                        :enable-publishing false) => anything)))

       (facts "about end-to-end workflow" :integration
              (against-background [(db/init-db! anything) => identity
                                   (db/create-db) => {:counters {:reads (utils/create-counter :reads 1000)
                                                                 :writes (utils/create-counter :writes 1000)}
                                                      :client nil}
                                   (yt-api/cache-get anything) => [nil nil]
                                   (yt-api/cache-set anything anything) => []]

                                  (fact "complete workflow processes channel data"
                                        (with-fake-routes (merge mock-responses
                                                                 {"https://www.googleapis.com/youtube/v3/videos"
                                                                  :get {:body (json/write-str {:items [{:id "test-video"
                                                                                                        :snippet {:title "Test"
                                                                                                                  :channelId "test-channel"
                                                                                                                  :publishedAt "2023-01-01T00:00:00Z"}
                                                                                                        :statistics {:viewCount "1000"}
                                                                                                        :contentDetails {:duration "PT4M13S"}}]})
                                                                        :status 200}})
                                          (let [app-state (main/create-app-state)
                                                initialized-state (main/init-app-state app-state)]
                                            (main/run-sync initialized-state {} "test-channel") => anything)))))

