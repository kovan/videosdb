(ns videosdb.youtube-api-test
  "YouTube API client tests."
  (:require [clojure.test :refer [deftest is testing]]
            [videosdb.youtube-api :as yt]
            [videosdb.cache :as cache]))

(deftest test-cache-key-func
  (testing "Cache key generation matches Python logic"
    (is (= "playlists?id=PLtest&part=snippet"
           (cache/key-func "/playlists" {"part" "snippet" "id" "PLtest"})))

    (is (= "playlists?id=PLtest&part=snippet"
           (cache/key-func "/playlists" {"part" "snippet" "id" "PLtest" "key" "secret"}))
        "API key should be excluded")))

(deftest test-cache-key-func-sorted
  (testing "Cache key params are sorted"
    (is (= "videos?id=abc&part=snippet,contentDetails,statistics"
           (cache/key-func "/videos" {"part" "snippet,contentDetails,statistics"
                                       "id"   "abc"})))))

(deftest test-make-client
  (testing "Client creation with defaults"
    (let [client (yt/make-client {:yt-key "test-key"})]
      (is (= "test-key" (:api-key client)))
      (is (some? (:http-client client)))
      (is (some? (:root-url client))))))

(deftest test-quota-exceeded-detection
  (testing "Quota exceeded exception data"
    (let [e (ex-info "YouTube API quota exceeded"
                     {:type :yt-quota-exceeded :status 403})]
      (is (yt/quota-exceeded? e)))))
