;; test/videosdb/core_test.clj
(ns videosdb.core-test
  (:require [clojure.test :refer :all]
            [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clojure.core.async :as async :refer [<! >! chan go]]
            [clojure.string :as str]
            [clojure.set :as set]
            [manifold.deferred :as d]
            [aleph.http :as http]
            [videosdb.db :as db]
            [videosdb.downloader :as downloader]
            [videosdb.publisher :as publisher]
            [videosdb.youtube-api :as yt]
            [videosdb.utils :as utils]))

;; Test Constants
(def test-constants
  {:video-ids #{"ZhI-stDIlCE" "ed7pFle2yM8" "J-1WVf5hFIk"
                "FBYoZ-FgC84" "QEkHcPt-Vpw" "HADeWBBb1so" "gavq4LM8XK0"}
   :playlist-id "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"
   :all-videos-playlist-id "UUcYzLCs3zrQIBVHYA1sK2sw"
   :video-id "HADeWBBb1so"
   :emulator-host "127.0.0.1:46456"
   :yt-channel-id "UCcYzLCs3zrQIBVHYA1sK2sw"})

;; Test Data Management
(defn data-dir []
  (str (System/getProperty "user.dir") "/test/test_data"))

(defn read-test-file [filename]
  (-> (str (data-dir) "/" filename)
      slurp
      (json/read-str :key-fn keyword)))

;; Test Environment Setup
(defn create-test-environment []
  {:db-config {:emulator-host (:emulator-host test-constants)
               :project-id "demo-project"}
   :redis-config {:db 1}
   :mock-responses (create-mock-responses)})

(defn create-mock-responses []
  (let [{:keys [yt-channel-id playlist-id all-videos-playlist-id video-ids]} test-constants]
    (-> {}
        ;; Channel responses
        (assoc [:channels {:channelId yt-channel-id}]
               (read-test-file (str "channel-" yt-channel-id ".response.json")))

        ;; Channel sections
        (assoc [:channelSections {:channelId yt-channel-id}]
               (read-test-file (str "channelSections-" yt-channel-id ".response.json")))

        ;; Playlist responses
        (assoc [:playlists {:id playlist-id}]
               (read-test-file (str "playlist-" playlist-id ".response.json")))
        (assoc [:playlists {:id all-videos-playlist-id}]
               (read-test-file (str "playlist-" all-videos-playlist-id ".response.json")))
        (assoc [:playlists {:channelId yt-channel-id}]
               (read-test-file "playlist-empty.response.json"))

        ;; Playlist items with pagination
        (assoc [:playlistItems {:playlistId playlist-id :page 0}]
               (read-test-file (str "playlistItems-" playlist-id ".response.0.json")))
        (assoc [:playlistItems {:playlistId playlist-id :page 1}]
               (read-test-file (str "playlistItems-" playlist-id ".response.1.json")))
        (assoc [:playlistItems {:playlistId all-videos-playlist-id}]
               (read-test-file (str "playlistItems-" all-videos-playlist-id ".response.json")))

        ;; Video responses
        (into {} (map (fn [vid]
                        [[:videos {:id vid}]
                         (read-test-file (str "video-" vid ".response.json"))])
                      video-ids)))))

;; Mock HTTP Client
(defn create-mock-http [mock-responses]
  (fn [endpoint params]
    (let [key [endpoint params]]
      (if-let [response (get mock-responses key)]
        (d/success-deferred {:status 200 :body response})
        (d/error-deferred (ex-info "Mock not found" {:endpoint endpoint :params params}))))))

;; Test Database Operations
(defn clear-test-databases [env]
  (d/chain
   ;; Clear Firestore emulator
   (http/delete (str "http://" (:emulator-host test-constants)
                     "/emulator/v1/projects/demo-project/databases/(default)/documents"))
   ;; Clear Redis
   (fn [_] (utils/redis-flush-db (:redis-config env)))))

(defn setup-test-db [env]
  (d/chain
   (clear-test-databases env)
   (fn [_]
     {:db-client (db/create-client (:db-config env))
      :redis-client (utils/create-redis-client (:redis-config env))})))

;; Core Test Functions
(defn test-downloader-process [env mock-http]
  (d/chain
   (setup-test-db env)
   (fn [{:keys [db-client redis-client]}]
     (let [config {:db-client db-client
                   :redis-client redis-client
                   :channel-id (:yt-channel-id test-constants)
                   :http-client mock-http}]
       (d/chain
        (downloader/check-for-new-videos config)
        (fn [_] {:db-client db-client :redis-client redis-client}))))))

(defn verify-playlists-created [db-client]
  (d/chain
   (db/list-collection db-client "playlists")
   (fn [playlists]
     (is (= 1 (count playlists)))
     (is (= (:playlist-id test-constants)
            (-> playlists first :id))))))

(defn verify-videos-created [db-client]
  (d/chain
   (db/list-collection db-client "videos")
   (fn [videos]
     (let [excluded-video "FBYoZ-FgC84"]
       (is (= 6 (count videos)))
       (doseq [video videos]
         (is (contains? (:video-ids test-constants) (:id video)))
         (is (not= excluded-video (:id video)))
         (is (get-in video [:videosdb :slug])))))))

(defn verify-playlist-data [db-client]
  (d/chain
   (db/get-document db-client "playlists" (:playlist-id test-constants))
   (fn [playlist]
     (is (= "youtube#playlist" (:kind playlist)))
     (is (= (:playlist-id test-constants) (:id playlist)))
     (let [videosdb (:videosdb playlist)]
       (is (= "how-to-be-really-successful-sadhguru-answers" (:slug videosdb)))
       (is (= 7 (:videoCount videosdb)))
       (is (= (:video-ids test-constants) (set (:videoIds videosdb))))))))

(defn verify-video-data [db-client]
  (d/chain
   (db/get-document db-client "videos" (:video-id test-constants))
   (fn [video]
     (is (= "youtube#video" (:kind video)))
     (is (= (:video-id test-constants) (:id video)))
     (is (= #{(:playlist-id test-constants)}
            (set (get-in video [:videosdb :playlists]))))
     (is (= "fate-god-luck-or-effort-what-decides-your-success-sadhguru"
            (get-in video [:videosdb :slug])))
     (is (get-in video [:videosdb :descriptionTrimmed]))
     (is (= 470.0 (get-in video [:videosdb :durationSeconds])))
     (is (inst? (get-in video [:snippet :publishedAt])))
     (is (:statistics video)))))

(defn verify-cache-populated [redis-client]
  (let [cache-key (yt/cache-key-fn "/playlistItems"
                                   {:part "snippet"
                                    :playlistId (:playlist-id test-constants)})]
    (d/chain
     (utils/redis-get redis-client cache-key)
     (fn [cached]
       (is (some? cached))
       (let [parsed (json/read-str cached :key-fn keyword)]
         (is (= "WMsDqOm6raLZmN3legOjPB7T3XI" (:etag parsed)))
         (is (= 2 (:n_pages parsed))))))))

;; Main Integration Test
(deftest test-full-integration
  (testing "Full downloader integration test"
    (let [env (create-test-environment)
          mock-http (create-mock-http (:mock-responses env))]
      @(d/chain
        (test-downloader-process env mock-http)
        (fn [{:keys [db-client redis-client]}]
          (d/zip
           (verify-playlists-created db-client)
           (verify-videos-created db-client)
           (verify-playlist-data db-client)
           (verify-video-data db-client)
           (verify-cache-populated redis-client)))))))

;; Export to Emulator Test
(defn test-export-to-emulator-fn [env]
  (d/chain
   (setup-test-db env)
   (fn [{:keys [db-client]}]
     (let [test-path "test_collection/test_document"
           test-data {:test-field "test value"}
           video-data (-> (read-test-file (str "video-" (:video-id test-constants) ".response.json"))
                          :items first)
           export-config {:enabled true
                          :emulator-host (:emulator-host test-constants)
                          :source-client db-client}]
       (d/chain
        ;; Setup test document
        (db/set-document db-client test-path test-data)

        ;; Run export
        (fn [_] (downloader/export-to-emulator export-config video-data))
        (fn [_] (downloader/export-pending-collections export-config))

        ;; Verify export
        (fn [_]
          (let [emulator-client (db/create-client {:emulator-host (:emulator-host test-constants)
                                                   :project-id "demo-project"})]
            (d/chain
             (db/get-document emulator-client test-path)
             (fn [exported-doc]
               (is (= test-data exported-doc)))))))))))

(deftest test-export-to-emulator
  (testing "Export to emulator functionality"
    (let [env (create-test-environment)]
      @(test-export-to-emulator-fn env))))

;; Utility Function Tests
(deftest test-cache-functions
  (testing "Cache key generation"
    (let [url "/test"
          params {:part "snippet" :id "test123" :key "api-key"}
          expected "test?id=test123&part=snippet"]
      (is (= expected (yt/cache-key-fn url params)))))

  (testing "YouTube ID parsing"
    (is (= "dQw4w9WgXcQ" (yt/parse-youtube-id "[dQw4w9WgXcQ].mp4")))
    (is (nil? (yt/parse-youtube-id "invalid-format.mp4")))))

;; Video Processing Function Tests  
(deftest test-video-processing
  (testing "Slug generation"
    (is (= "test-video-title" (downloader/create-slug "Test Video Title!")))
    (is (= "another-test-more" (downloader/create-slug "Another-Test & More"))))

  (testing "Description trimming"
    (let [desc "This is a description #Sadhguru with more text"]
      (is (= "This is a description "
             (downloader/trim-description desc "#Sadhguru")))
      (is (= desc (downloader/trim-description desc "#NotFound"))))))

;; Publisher Tests
(deftest test-publisher-functions
  (testing "Twitter post text creation"
    (let [video {:id "test123"
                 :snippet {:title "Test Video Title"}
                 :videosdb {:slug "test-video-title"}}
          config {:hostname "https://example.com"}]
      @(d/chain
        (publisher/create-post-text video config)
        (fn [post-text]
          (is (str/includes? post-text "Test Video Title"))
          (is (str/includes? post-text "http://youtu.be/test123")))))))

;; Database Operation Tests
(deftest test-database-operations
  (testing "Basic database operations"
    (let [env (create-test-environment)]
      @(d/chain
        (setup-test-db env)
        (fn [{:keys [db-client]}]
          (let [test-doc {:id "test123" :title "Test Document"}]
            (d/chain
             ;; Test document creation
             (db/set-document db-client "test/doc1" test-doc)

             ;; Test document retrieval
             (fn [_] (db/get-document db-client "test/doc1"))
             (fn [retrieved]
               (is (= test-doc retrieved))

               ;; Test document update
               (db/update-document db-client "test/doc1" {:title "Updated Title"}))

             ;; Verify update
             (fn [_] (db/get-document db-client "test/doc1"))
             (fn [updated]
               (is (= "Updated Title" (:title updated)))
               (is (= "test123" (:id updated)))

               ;; Test collection operations
               (db/set-document db-client "test/doc2" {:id "test456"}))

             ;; Test listing documents
             (fn [_] (db/list-collection db-client "test"))
             (fn [docs]
               (is (= 2 (count docs)))))))))))

;; Error Handling Tests
(deftest test-quota-handling
  (testing "Quota exceeded detection"
    (let [quota-response {:status 403
                          :body {:error {:code 403
                                         :message "Quota exceeded"}}}]
      (is (utils/quota-exceeded? quota-response)))))

;; Concurrent Operations Test
(deftest test-concurrent-operations
  (testing "Concurrent database operations"
    (let [env (create-test-environment)
          concurrent-count 10
          test-docs (map #(hash-map :id (str "test" %) :value %)
                         (range concurrent-count))]
      @(d/chain
        (setup-test-db env)
        (fn [{:keys [db-client]}]
          (d/chain
           ;; Concurrent writes
           (d/zip (map #(db/set-document db-client
                                         (str "concurrent/doc" (:id %)) %)
                       test-docs))

           ;; Verify all written
           (fn [_] (db/list-collection db-client "concurrent"))
           (fn [docs]
             (is (= concurrent-count (count docs))))))))))

;; Test Data Creation Helpers
(defn create-test-video-data [video-id title]
  {:id video-id
   :kind "youtube#video"
   :snippet {:title title
             :channelId (:yt-channel-id test-constants)
             :publishedAt "2022-07-06T12:18:45Z"
             :description "Test video description"}
   :contentDetails {:duration "PT7M50S"}
   :statistics {:viewCount "1000" :likeCount "100"}
   :videosdb {:slug (downloader/create-slug title)
              :playlists [(:playlist-id test-constants)]}})

(defn create-test-playlist-data [playlist-id title video-ids]
  {:id playlist-id
   :kind "youtube#playlist"
   :snippet {:title title
             :channelTitle "Test Channel"}
   :videosdb {:slug (downloader/create-slug title)
              :videoCount (count video-ids)
              :videoIds video-ids}})

;; Mock Transcript API
(defn mock-transcript-api [video-id]
  (if (contains? #{"HADeWBBb1so" "ed7pFle2yM8"} video-id)
    [{:text "This is a test transcript" :start 0.0 :duration 5.0}
     {:text "for video testing purposes" :start 5.0 :duration 5.0}]
    (throw (ex-info "Transcript not available" {:video-id video-id}))))

;; Performance Test
(deftest test-memory-usage
  (testing "Memory usage during processing"
    (let [env (create-test-environment)
          mock-http (create-mock-http (:mock-responses env))
          initial-memory (.totalMemory (Runtime/getRuntime))]
      @(d/chain
        (test-downloader-process env mock-http)
        (fn [_]
          (System/gc) ; Force garbage collection
          (let [final-memory (.totalMemory (Runtime/getRuntime))
                memory-diff (- final-memory initial-memory)]
            ;; Should not increase memory by more than 100MB
            (is (< memory-diff (* 100 1024 1024)))))))))

;; Full Pipeline Integration Test
(deftest test-full-pipeline
  (testing "Complete pipeline from start to finish"
    (let [env (create-test-environment)
          mock-http (create-mock-http (:mock-responses env))]
      @(d/chain
        (setup-test-db env)
        (fn [{:keys [db-client redis-client]}]
          (let [config {:db-client db-client
                        :redis-client redis-client
                        :channel-id (:yt-channel-id test-constants)
                        :http-client mock-http
                        :enable-transcripts false
                        :enable-twitter-publishing false
                        :export-to-emulator-host (:emulator-host test-constants)}]
            (d/chain
             ;; Run complete pipeline
             (downloader/run-complete-pipeline config)

             ;; Verify end-to-end results
             (fn [_]
               (d/zip
                (db/list-collection db-client "videos")
                (db/list-collection db-client "playlists")
                (db/get-document db-client "meta/video_ids")))

             (fn [[videos playlists meta]]
               ;; Verify we have expected data
               (is (pos? (count videos)))
               (is (pos? (count playlists)))
               (is (pos? (count (:videoIds meta))))

               ;; Verify data integrity
               (doseq [video videos]
                 (is (string? (:id video)))
                 (is (get-in video [:videosdb :slug]))
                 (is (number? (get-in video [:videosdb :durationSeconds]))))

               (doseq [playlist playlists]
                 (is (string? (:id playlist)))
                 (is (get-in playlist [:videosdb :slug]))
                 (is (number? (get-in playlist [:videosdb :videoCount]))))))))))))

;; Test Runner
(defn run-all-tests []
  "Runs all tests and returns results"
  (println "Starting videosdb tests...")
  (let [start-time (System/currentTimeMillis)
        results (run-tests 'videosdb.core-test)
        end-time (System/currentTimeMillis)
        duration (- end-time start-time)]
    (println (str "Tests completed in " duration "ms"))
    (println (str "Ran " (:test results) " tests"))
    (println (str "Passed: " (:pass results)))
    (println (str "Failed: " (:fail results)))
    (println (str "Errors: " (:error results)))
    results))

;; Main entry point for testing
(defn -main [& args]
  "Main entry point for running tests"
  (let [results (run-all-tests)]
    (System/exit (if (and (zero? (:fail results))
                          (zero? (:error results)))
                   0 1))))