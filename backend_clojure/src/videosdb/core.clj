
;; ============================================================================
;; src/videosdb/core.clj - Main entry point
;; ============================================================================

(ns videosdb.core
  (:require [clojure.tools.logging :as log]
            [videosdb.db :as db]
            [videosdb.downloader :as downloader]
            [videosdb.settings :as settings]
            [environ.core :refer [env]]))

(defn -main [& args]
  (log/info "Starting VideosDB")
  (let [channel-id (env :youtube-channel-id)
        options {:enable-transcripts (= "true" (env :enable-transcripts))
                 :enable-twitter-publishing (= "true" (env :enable-twitter-publishing))
                 :export-to-emulator-host (env :export-to-emulator-host)}
        db-state (db/create-db)
        db-state (db/init-db! db-state)]
    (downloader/check-for-new-videos db-state options channel-id)))