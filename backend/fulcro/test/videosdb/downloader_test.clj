(ns videosdb.downloader-test
  "Downloader / sync orchestrator tests."
  (:require [clojure.test :refer [deftest is testing]]
            [videosdb.downloader :as dl]))

(deftest test-slugify
  (testing "Slug generation"
    (is (= "hello-world" (dl/slugify "Hello World")))
    (is (= "test-video-123" (dl/slugify "Test Video 123")))
    (is (= "special-chars" (dl/slugify "Special! @Chars#")))
    (is (= "multiple-spaces" (dl/slugify "Multiple   Spaces")))
    (is (= "leading-trailing" (dl/slugify "  Leading Trailing  ")))
    (is (nil? (dl/slugify nil)))))

(deftest test-parse-duration-seconds
  (testing "ISO 8601 duration parsing"
    (is (= 3723.0 (dl/parse-duration-seconds "PT1H2M3S")))
    (is (= 120.0 (dl/parse-duration-seconds "PT2M")))
    (is (= 30.0 (dl/parse-duration-seconds "PT30S")))
    (is (= 3600.0 (dl/parse-duration-seconds "PT1H")))
    (is (= 0.0 (dl/parse-duration-seconds "invalid")))))

(deftest test-linkify-description
  (testing "URL linkification"
    (is (= "Visit <a href=\"https://example.com\" rel=\"nofollow\">https://example.com</a> for more"
           (dl/linkify-description "Visit https://example.com for more")))
    (is (= "No links here"
           (dl/linkify-description "No links here")))
    (is (nil? (dl/linkify-description nil)))))

(deftest test-parse-iso-datetime
  (testing "ISO datetime parsing"
    (let [d (dl/parse-iso-datetime "2023-01-15T10:30:00Z")]
      (is (instance? java.util.Date d)))
    (is (nil? (dl/parse-iso-datetime nil)))
    (is (nil? (dl/parse-iso-datetime "not-a-date")))))
