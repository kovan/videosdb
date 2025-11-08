


;; ============================================================================
;; Main application functions and examples
;; ============================================================================

(ns videosdb.main
  (:require [videosdb.core :as core]
            [videosdb.db :as db]
            [videosdb.downloader :as downloader]
            [videosdb.publisher :as publisher]
            [videosdb.ipfs :as ipfs]
            [videosdb.settings :as settings]
            [clojure.tools.logging :as log]))

;; Application state management (pure functions)
(defn create-app-state []
  {:db-state (db/create-db)
   :ipfs-client (ipfs/create-ipfs-client)
   :start-time (System/currentTimeMillis)})

(defn init-app-state [app-state]
  (update app-state :db-state db/init-db!))

(defn run-sync [app-state options channel-id]
  (downloader/check-for-new-videos (:db-state app-state) options channel-id))

(defn run-ipfs-sync [app-state]
  (ipfs/download-and-register-folder (:db-state app-state) (:ipfs-client app-state)))

;; Utility functions for running different operations
(defn sync-videos
  "Main video synchronization function"
  [& {:keys [channel-id enable-transcripts enable-publishing export-to-emulator]
      :or {channel-id "UCcYzLCs3zrQIBVHYA1sK2sw"
           enable-transcripts false
           enable-publishing false
           export-to-emulator nil}}]
  (let [app-state (create-app-state)
        app-state (init-app-state app-state)
        options {:enable-transcripts enable-transcripts
                 :enable-twitter-publishing enable-publishing
                 :export-to-emulator-host export-to-emulator}]
    (run-sync app-state options channel-id)))

(defn sync-ipfs
  "IPFS synchronization function"
  []
  (let [app-state (create-app-state)
        app-state (init-app-state app-state)]
    (run-ipfs-sync app-state)))

(defn publish-videos
  "Manually trigger video publishing"
  [& {:keys [channel-id] :or {channel-id "UCcYzLCs3zrQIBVHYA1sK2sw"}}]
  (let [app-state (create-app-state)
        app-state (init-app-state app-state)
        db-state (:db-state app-state)]

    ;; Get videos ready for publishing
    (let [video-ids-doc (db/db-get-noquota db-state "meta/video_ids")
          video-ids (when (.exists video-ids-doc)
                      (get (.getData video-ids-doc) "videoIds" []))]

      (doseq [video-id (take 10 video-ids)] ; Limit to 10 for safety
        (try
          (let [video-doc (db/db-get-noquota db-state (str "videos/" video-id))]
            (when (.exists video-doc)
              (let [video-data (.getData video-doc)]
                (when (not (empty? (get-in video-data [:videosdb :slug])))
                  (publisher/publish-video db-state video-data)))))
          (catch Exception e
            (log/error e (format "Error publishing video %s" video-id))))))))

;; Command-line interface functions
(defn print-stats []
  (let [app-state (create-app-state)
        app-state (init-app-state app-state)]
    (println "Database Stats:")
    (doseq [stat (db/get-stats (:db-state app-state))]
      (println " " stat))
    (println "Cache Stats:")
    (doseq [[k v] (videosdb.youtube-api/cache-stats)]
      (println " " k ":" v))))

;; Example usage and testing functions
(comment
  ;; Basic video sync
  (sync-videos :channel-id "UCcYzLCs3zrQIBVHYA1sK2sw"
               :enable-transcripts true
               :enable-publishing false)

  ;; IPFS sync
  (sync-ipfs)

  ;; Manual publishing
  (publish-videos)

  ;; Print current stats
  (print-stats)

  ;; Direct database operations
  (let [app-state (-> (create-app-state) init-app-state)
        db-state (:db-state app-state)]

    ;; Get video count
    (let [video-ids-doc (db/db-get-noquota db-state "meta/video_ids")]
      (when (.exists video-ids-doc)
        (count (get (.getData video-ids-doc) "videoIds" []))))

    ;; Get a specific video
    (let [video-doc (db/db-get-noquota db-state "videos/some-video-id")]
      (when (.exists video-doc)
        (.getData video-doc))))

  ;; YouTube API operations
  (let [[modified channel] (videosdb.youtube-api/get-channel-info "UCcYzLCs3zrQIBVHYA1sK2sw")]
    (println "Channel:" (get-in channel [:snippet :title]))
    (println "Subscriber count:" (get-in channel [:statistics :subscriberCount])))

  ;; Cache operations
  (println "Cache stats:" (videosdb.youtube-api/cache-stats)))

;; Environment configuration helper
(defn setup-environment! []
  (println "Setting up environment variables...")
  (System/setProperty "YOUTUBE_CHANNEL_ID" "UCcYzLCs3zrQIBVHYA1sK2sw")
  (System/setProperty "VIDEOSDB_CONFIG" "testing")
  (System/setProperty "FIREBASE_PROJECT" "videosdb-testing")
  (System/setProperty "LOGLEVEL" "info")
  (println "Environment configured for testing"))

;; Main CLI entry point
(defn -main [& args]
  (case (first args)
    "sync" (sync-videos)
    "ipfs" (sync-ipfs)
    "publish" (publish-videos)
    "stats" (print-stats)
    "setup" (setup-environment!)
    (do (println "Usage: lein run [sync|ipfs|publish|stats|setup]")
        (println "  sync    - Synchronize videos from YouTube")
        (println "  ipfs    - Sync videos to IPFS")
        (println "  publish - Publish videos to social media")
        (println "  stats   - Show current statistics")
        (println "  setup   - Setup test environment"))))

;; ============================================================================
;; Configuration and Setup Guide
;; ============================================================================

;; Required environment variables:
;; YOUTUBE_CHANNEL_ID - YouTube channel to sync
;; YOUTUBE_API_KEY - YouTube Data API key
;; VIDEOSDB_CONFIG - Config name (testing/production)
;; FIREBASE_PROJECT - Firebase project ID
;; VIDEOSDB_HOSTNAME - Website hostname
;; LOGLEVEL - Logging level

;; Required files:
;; common/keys/{config}.json - Firebase service account keys
;; common/firebase/db-schema.json - Database schema

;; Redis must be running on localhost:6379

;; Example usage:
;; lein run sync     # Full synchronization
;; lein run publish  # Publish pending videos
;; lein run stats    # Show statistics