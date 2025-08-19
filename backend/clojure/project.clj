;; ============================================================================
;; project.clj - Leiningen project configuration
;; ============================================================================

(defproject videosdb "1.0.0"
  :description "VideosDB - YouTube video management system (Functional)"
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [org.clojure/core.async "1.6.673"]
                 [org.clojure/data.json "2.4.0"]
                 [org.clojure/tools.logging "1.2.4"]
                 [com.google.cloud/google-cloud-firestore "RELEASE"]
                 [com.google.auth/google-auth-library-oauth2-http "1.19.0"]
                 [clj-http "3.12.3"]
                 [com.taoensso/carmine "3.5.0-alpha11"]
                 [manifold "0.3.0"]
                 [clj-time "0.15.2"]
                 [cheshire "5.11.0"]
                 [slugger "1.0.1"]
                 [environ "1.2.0"]
                 [com.taoensso/timbre "6.2.2"]]
  :repositories [["central" {:url "https://repo1.maven.org/maven2/"}]]
  :main videosdb.core)
