(ns videosdb.config
  "Environment-based configuration. Replaces settings.py."
  (:require [clojure.tools.logging :as log]
            [clojure.java.io :as io]
            [clojure.data.json :as json]))

(defn env
  "Get an environment variable with optional default."
  ([k] (System/getenv k))
  ([k default] (or (System/getenv k) default)))

(defn config
  "Return the current config map from environment variables."
  []
  {:videosdb-config    (env "VIDEOSDB_CONFIG" "testing")
   :youtube-channel-id (env "YOUTUBE_CHANNEL_ID")
   :youtube-api-key    (env "YOUTUBE_API_KEY")
   :youtube-api-url    (env "YOUTUBE_API_URL" "https://www.googleapis.com/youtube/v3")
   :firebase-project   (env "FIREBASE_PROJECT" "videosdb-testing")
   :firestore-emulator (env "FIRESTORE_EMULATOR_HOST")
   :redis-url          (env "REDIS_URL" "redis://localhost:6379")
   :log-level          (env "LOGLEVEL" "INFO")
   :title              (env "VIDEOSDB_TITLE")
   :subtitle           (env "VIDEOSDB_SUBTITLE")
   :hostname           (env "VIDEOSDB_HOSTNAME")
   :website            (env "VIDEOSDB_WEBSITE")
   :cse-url            (env "VIDEOSDB_CSE_URL")})

(defn common-dir
  "Resolve the common/ directory relative to the project."
  []
  (let [candidates ["../../common" "../common" "common"]]
    (or (first (filter #(.exists (io/file %)) candidates))
        "../../common")))

(defn service-account-path
  "Path to the service account JSON key file."
  []
  (let [cfg (env "VIDEOSDB_CONFIG" "testing")]
    (str (common-dir) "/keys/" (.replace cfg "\"" "") ".json")))

(defn db-schema
  "Load the Firestore document JSON Schema."
  []
  (let [path (str (common-dir) "/firebase/db-schema.json")]
    (when (.exists (io/file path))
      (json/read-str (slurp path) :key-fn keyword))))

(defn firebase-config
  "Load the Firebase app config JSON for the current config."
  []
  (let [cfg  (env "VIDEOSDB_CONFIG" "testing")
        path (str (common-dir) "/firebase/configs/" cfg ".json")]
    (when (.exists (io/file path))
      (json/read-str (slurp path) :key-fn keyword))))

(defn emulator?
  "True if the Firestore emulator is configured."
  []
  (some? (env "FIRESTORE_EMULATOR_HOST")))
