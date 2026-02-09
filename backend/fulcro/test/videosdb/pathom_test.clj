(ns videosdb.pathom-test
  "Pathom resolver tests."
  (:require [clojure.test :refer [deftest is testing use-fixtures]]
            [videosdb.server.pathom :as pathom]
            [videosdb.firestore :as fs]
            [videosdb.config :as config]))

(def ^:dynamic *env* nil)

(defn emulator-fixture [f]
  (when (config/emulator?)
    (let [db  (fs/create-client)
          env (pathom/make-env db)]
      ;; Seed test data
      (fs/set-doc db "videos/testv1"
                  {:id "testv1"
                   :snippet {:title "Test Video"
                             :description "A test"
                             :publishedAt (java.util.Date.)
                             :channelId "ch1"
                             :channelTitle "Test Channel"
                             :thumbnails {:medium {:url "http://img.test/1.jpg"}}
                             :tags ["tag1" "tag2"]}
                   :videosdb {:slug "test-video"
                              :durationSeconds 300.0
                              :descriptionTrimmed "A test"
                              :playlists ["pl1"]}
                   :statistics {:viewCount 1000
                                :likeCount 50
                                :commentCount 10
                                :favoriteCount 5}
                   :contentDetails {:duration "PT5M"}})

      (fs/set-doc db "playlists/pl1"
                  {:id "pl1"
                   :snippet {:title "Test Playlist"
                             :description "A test playlist"
                             :thumbnails {:medium {:url "http://img.test/pl1.jpg"}}}
                   :videosdb {:slug "test-playlist"
                              :videoCount 10
                              :lastUpdated (java.util.Date.)
                              :videoIds #{"testv1"}}})

      (fs/set-doc db "meta/video_ids" {:videoIds ["testv1"]})

      (binding [*env* env]
        (fs/reset-counters!)
        (f)))))

(use-fixtures :each emulator-fixture)

(deftest test-all-playlists-resolver
  (when *env*
    (testing "All playlists resolver"
      (let [result (pathom/process *env* [{:all-playlists [:playlist/id
                                                            :playlist/title
                                                            :playlist/slug]}])]
        (is (seq (:all-playlists result)))
        (is (= "Test Playlist" (-> result :all-playlists first :playlist/title)))))))

(deftest test-meta-video-ids-resolver
  (when *env*
    (testing "Meta video IDs resolver"
      (let [result (pathom/process *env* [:meta/video-ids])]
        (is (seq (:meta/video-ids result)))))))
