(ns videosdb.firestore-test
  "Firestore client tests. Run against emulator."
  (:require [clojure.test :refer [deftest is testing use-fixtures]]
            [videosdb.firestore :as fs]
            [videosdb.config :as config]))

(def ^:dynamic *db* nil)

(defn emulator-fixture [f]
  (when (config/emulator?)
    (let [db (fs/create-client)]
      (binding [*db* db]
        (fs/reset-counters!)
        (f)))))

(use-fixtures :each emulator-fixture)

(deftest test-set-and-get-doc
  (when *db*
    (testing "Set and get a document"
      (fs/set-doc *db* "test/doc1" {:name "Test" :value 42})
      (let [doc (fs/get-doc *db* "test/doc1")]
        (is (= "Test" (:name doc)))
        (is (= 42 (:value doc)))))))

(deftest test-update-doc
  (when *db*
    (testing "Update a document"
      (fs/set-doc *db* "test/doc2" {:name "Original" :count 0})
      (fs/update-doc *db* "test/doc2" {:count 5})
      (let [doc (fs/get-doc *db* "test/doc2")]
        (is (= "Original" (:name doc)))
        (is (= 5 (:count doc)))))))

(deftest test-delete-doc
  (when *db*
    (testing "Delete a document"
      (fs/set-doc *db* "test/doc3" {:name "Deleteme"})
      (fs/delete-doc *db* "test/doc3")
      (is (nil? (fs/get-doc *db* "test/doc3"))))))

(deftest test-init-meta
  (when *db*
    (testing "Initialize meta documents"
      (fs/init-meta! *db*)
      (let [video-ids (fs/get-doc *db* "meta/video_ids")
            state     (fs/get-doc *db* "meta/state")]
        (is (some? video-ids))
        (is (vector? (:videoIds video-ids)))
        (is (some? state))))))

(deftest test-query-videos
  (when *db*
    (testing "Query videos collection"
      ;; Insert test videos
      (fs/set-doc *db* "videos/test1"
                  {:id "test1"
                   :snippet {:title "Test Video 1"
                             :publishedAt (java.util.Date.)}
                   :videosdb {:slug "test-video-1"
                              :durationSeconds 120.0
                              :playlists ["pl1"]}
                   :statistics {:viewCount 100}})
      (let [results (fs/query-videos *db*
                                     {:order-by ["snippet.publishedAt" :desc]
                                      :limit    10})]
        (is (vector? results))))))

(deftest test-quota-tracking
  (when *db*
    (testing "Quota counters increment"
      (fs/reset-counters!)
      (fs/set-doc *db* "test/quota1" {:x 1})
      (fs/get-doc *db* "test/quota1")
      (let [{:keys [reads writes]} (fs/get-stats)]
        (is (pos? reads))
        (is (pos? writes))))))
