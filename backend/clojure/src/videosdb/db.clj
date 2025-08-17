

;; ============================================================================
;; src/videosdb/db.clj - Database operations (Functional)
;; ============================================================================

(ns videosdb.db
  (:require [clojure.tools.logging :as log]
            [clojure.data.json :as json]
            [clojure.java.io :as io]
            [videosdb.utils :as utils]
            [environ.core :refer [env]])
  (:import [com.google.cloud.firestore Firestore FirestoreOptions]
           [com.google.auth.oauth2 ServiceAccountCredentials]
           [java.io FileInputStream]))

;; Database configuration
(def db-config
  {:free-tier-write-quota 20000
   :free-tier-read-quota 50000})

;; Client creation
(defn get-client
  ([] (get-client nil nil))
  ([project] (get-client project nil))
  ([project config]
   (let [config (or config (env :videosdb-config "testing"))
         project (or project (env :firebase-project "videosdb-testing"))
         base-dir (System/getProperty "user.dir")
         common-dir (str base-dir "/common")
         creds-path (str common-dir "/keys/" (clojure.string/replace config "\"" "") ".json")]

     (if (env :firestore-emulator-host)
       (do (log/info "USING EMULATOR:" (env :firestore-emulator-host))
           (-> (FirestoreOptions/newBuilder)
               (.setProjectId "demo-project")
               (.setHost (env :firestore-emulator-host))
               (.setCredentials (ServiceAccountCredentials/fromStream
                                 (FileInputStream. creds-path)))
               (.build)
               (.getService)))
       (do (log/info "USING LIVE DATABASE")
           (log/info "Current project:" project)
           (log/info "Current config:" config)
           (-> (FirestoreOptions/newBuilder)
               (.setProjectId project)
               (.setCredentials (ServiceAccountCredentials/fromStream
                                 (FileInputStream. creds-path)))
               (.build)
               (.getService)))))))

;; Database state creation
(defn create-db []
  (let [counters {:reads (utils/create-counter :reads (- (:free-tier-read-quota db-config) 5000))
                  :writes (utils/create-counter :writes (- (:free-tier-write-quota db-config) 500))}
        base-dir (System/getProperty "user.dir")
        common-dir (str base-dir "/common")
        schema-path (str common-dir "/firebase/db-schema.json")
        db-schema (when (.exists (io/file schema-path))
                    (json/read-str (slurp schema-path) :key-fn keyword))
        db-client (get-client)]
    {:counters counters
     :db-schema db-schema
     :client db-client}))

;; Database initialization
(defn init-db! [db-state]
  (let [client (:client db-state)]
    ;; Initialize meta collections
    (let [video-ids-doc (.document client "meta/video_ids")
          video-ids-snap (.get video-ids-doc)]
      (when (or (not (.exists video-ids-snap))
                (not (contains? (.getData video-ids-snap) "videoIds")))
        (.set video-ids-doc {"videoIds" []})))

    (let [state-doc (.document client "meta/state")
          state-snap (.get state-doc)]
      (when (not (.exists state-snap))
        (.set state-doc {})))

    ;; Test write operation
    (db-set! db-state "meta/test" {})
    db-state))

;; Counter operations
(defn increase-counter! [db-state counter-type & [increase]]
  (let [inc-val (or increase 1)]
    (utils/inc-counter! (get (:counters db-state) counter-type) inc-val)))

;; Database operations with quota tracking
(defn db-set! [db-state path data & [merge?]]
  (increase-counter! db-state :writes)
  (let [doc (.document (:client db-state) path)]
    (if merge?
      (.set doc data com.google.cloud.firestore.SetOptions/merge)
      (.set doc data))))

(defn db-get [db-state path]
  (increase-counter! db-state :reads)
  (.get (.document (:client db-state) path)))

(defn db-update! [db-state path data]
  (increase-counter! db-state :writes)
  (.update (.document (:client db-state) path) data))

(defn db-delete! [db-state path]
  (increase-counter! db-state :writes)
  (.delete (.document (:client db-state) path)))

;; Database operations without quota tracking
(defn db-set-noquota! [db-state path data & [merge?]]
  (let [doc (.document (:client db-state) path)]
    (if merge?
      (.set doc data com.google.cloud.firestore.SetOptions/merge)
      (.set doc data))))

(defn db-get-noquota [db-state path]
  (.get (.document (:client db-state) path)))

(defn db-update-noquota! [db-state path data]
  (.update (.document (:client db-state) path) data))

;; Statistics
(defn get-stats [db-state]
  (let [read-counter (get (:counters db-state) :reads)
        write-counter (get (:counters db-state) :writes)]
    #{(utils/counter-stats read-counter)
      (utils/counter-stats write-counter)}))

;; Schema validation
(defn validate-video-schema [db-state video-dict]
  ;; Schema validation would go here
  ;; For now, just check if video has an ID
  (boolean (and video-dict (:id video-dict))))