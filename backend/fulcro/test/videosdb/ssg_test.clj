(ns videosdb.ssg-test
  "Static site generation tests."
  (:require [clojure.test :refer [deftest is testing]]
            [videosdb.ssg.renderer :as renderer]
            [clojure.string :as str]))

(deftest test-wrap-html
  (testing "HTML document wrapping"
    (let [html (renderer/wrap-html
                {:title      "Test Page"
                 :description "A test page"
                 :canonical  "https://example.com/test"
                 :body       "<div>Hello</div>"
                 :state      {:test true}
                 :app-config {:title    "VideosDB"
                              :subtitle "Test"
                              :hostname "https://example.com"}})]
      (is (str/includes? html "<!DOCTYPE html>"))
      (is (str/includes? html "<title>Test Page</title>"))
      (is (str/includes? html "content=\"A test page\""))
      (is (str/includes? html "rel=\"canonical\""))
      (is (str/includes? html "<div>Hello</div>"))
      (is (str/includes? html "__FULCRO_INITIAL_STATE__"))
      (is (str/includes? html "main.js")))))

(deftest test-wrap-html-minimal
  (testing "HTML wrapping with minimal config"
    (let [html (renderer/wrap-html
                {:body       ""
                 :state      {}
                 :app-config {}})]
      (is (str/includes? html "<!DOCTYPE html>"))
      (is (str/includes? html "<div id=\"app\">")))))
