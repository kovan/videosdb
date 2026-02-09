(ns videosdb.firestore
  "Firestore Java SDK interop. Replaces db.py."
  (:require [clojure.tools.logging :as log]
            [clojure.data.json :as json]
            [videosdb.config :as config])
  (:import [com.google.auth.oauth2 GoogleCredentials]
           [com.google.cloud.firestore Firestore FirestoreOptions
            DocumentReference DocumentSnapshot
            Query Query$Direction FieldValue SetOptions]
           [com.google.firebase FirebaseApp FirebaseOptions]
           [com.google.firebase.cloud FirestoreClient]
           [java.io FileInputStream]
           [java.util HashMap ArrayList]))

;; --- Quota tracking ---

(def ^:private read-counter (atom 0))
(def ^:private write-counter (atom 0))

(def ^:private read-limit  45000)   ; 50K - 5K buffer
(def ^:private write-limit 19500)   ; 20K - 500 buffer

(defn- check-quota! [counter-atom limit type-name]
  (let [n (swap! counter-atom inc)]
    (when (> n limit)
      (throw (ex-info (str "Surpassed " type-name " ops limit of " limit)
                      {:type :quota-exceeded :counter n :limit limit})))))

(defn- inc-reads!  ([] (check-quota! read-counter read-limit "READS"))
                   ([n] (swap! read-counter + n)))
(defn- inc-writes! [] (check-quota! write-counter write-limit "WRITES"))

(defn get-stats []
  {:reads  @read-counter
   :writes @write-counter
   :read-limit  read-limit
   :write-limit write-limit})

(defn reset-counters! []
  (reset! read-counter 0)
  (reset! write-counter 0))

;; --- Clojure <-> Firestore data conversion ---

(defn- clj->firestore
  "Convert a Clojure data structure to Java types Firestore understands."
  [v]
  (cond
    (map? v)        (let [m (HashMap.)]
                      (doseq [[k val] v]
                        (.put m (name k) (clj->firestore val)))
                      m)
    (sequential? v) (let [a (ArrayList.)]
                      (doseq [item v]
                        (.add a (clj->firestore item)))
                      a)
    (keyword? v)    (name v)
    (instance? java.util.Date v) v
    :else           v))

(defn- firestore->clj
  "Convert Firestore Java types back to Clojure data."
  [v]
  (cond
    (instance? java.util.Map v)
    (persistent!
     (reduce (fn [m entry]
               (assoc! m (keyword (.getKey entry))
                       (firestore->clj (.getValue entry))))
             (transient {})
             (.entrySet v)))

    (instance? java.util.List v)
    (mapv firestore->clj v)

    (instance? com.google.cloud.Timestamp v)
    (.toDate v)

    :else v))

;; --- Client creation ---

(defn create-client
  "Create a Firestore client. Uses emulator if FIRESTORE_EMULATOR_HOST is set."
  ([] (create-client nil))
  ([{:keys [project]}]
   (let [emulator-host (config/env "FIRESTORE_EMULATOR_HOST")
         project-id    (or project
                           (if emulator-host
                             "demo-project"
                             (config/env "FIREBASE_PROJECT" "videosdb-testing")))
         cfg           (config/env "VIDEOSDB_CONFIG" "testing")
         creds-path    (config/service-account-path)]

     (when emulator-host
       (log/info "USING EMULATOR:" emulator-host))
     (when-not emulator-host
       (log/info "USING LIVE DATABASE"))
     (log/info "Current project:" project-id)
     (log/info "Current config:" cfg)

     (let [builder (-> (FirestoreOptions/newBuilder)
                       (.setProjectId project-id))]
       (when-not emulator-host
         (when (.exists (java.io.File. creds-path))
           (.setCredentials builder
                           (GoogleCredentials/fromStream
                            (FileInputStream. creds-path)))))
       (when emulator-host
         (.setEmulatorHost builder emulator-host))
       (.getService (.build builder))))))

;; --- CRUD operations ---

(defn get-doc
  "Get a document by path. Returns Clojure map or nil."
  ([^Firestore db path]
   (get-doc db path true))
  ([^Firestore db path track-quota?]
   (when track-quota? (inc-reads!))
   (let [ref  (.document db path)
         snap @(.get ref)]
     (when (.exists snap)
       (firestore->clj (.getData snap))))))

(defn set-doc
  "Set a document by path. Options: :merge true for merge semantics."
  ([^Firestore db path data]
   (set-doc db path data {}))
  ([^Firestore db path data {:keys [merge? no-quota?]}]
   (when-not no-quota? (inc-writes!))
   (let [ref      (.document db path)
         java-map (clj->firestore data)]
     (if merge?
       @(.set ref java-map (SetOptions/merge))
       @(.set ref java-map)))))

(defn update-doc
  "Update specific fields on a document."
  ([^Firestore db path updates]
   (update-doc db path updates {}))
  ([^Firestore db path updates {:keys [no-quota?]}]
   (when-not no-quota? (inc-writes!))
   (let [ref (.document db path)
         m   (clj->firestore updates)]
     @(.update ref ^java.util.Map m))))

(defn delete-doc
  "Delete a document by path."
  ([^Firestore db path]
   (delete-doc db path {}))
  ([^Firestore db path {:keys [no-quota?]}]
   (when-not no-quota? (inc-writes!))
   @(.delete (.document db path))))

(defn array-union
  "Create an ArrayUnion FieldValue for Firestore."
  [values]
  (FieldValue/arrayUnion (into-array Object values)))

;; --- Query helpers ---

(defn query-videos
  "Query the videos collection with options.
   opts keys:
     :order-by     - [field direction] e.g. [\"snippet.publishedAt\" :desc]
     :where-clause - [field op value] e.g. [\"videosdb.playlists\" :array-contains \"PLid\"]
     :start-after  - DocumentSnapshot cursor
     :limit        - number of results"
  [^Firestore db opts]
  (let [{:keys [order-by where-clause start-after limit collection-name]
         :or   {collection-name "videos"}} opts
        col   (.collection db collection-name)
        query (cond-> col
                order-by
                (.orderBy (first order-by)
                          (if (= (second order-by) :asc)
                            Query$Direction/ASCENDING
                            Query$Direction/DESCENDING))

                where-clause
                (.whereArrayContains ^String (nth where-clause 0) ^Object (nth where-clause 2))

                start-after
                (.startAfter (into-array Object [start-after]))

                limit
                (.limit (int limit)))]
    (inc-reads!)
    (let [results @(.get query)]
      (mapv (fn [snap]
              (assoc (firestore->clj (.getData snap))
                     :_snapshot snap))
            (.getDocuments results)))))

(defn query-collection
  "Query an entire collection, returning all docs as Clojure maps."
  [^Firestore db collection-name]
  (inc-reads!)
  (let [results @(.get (.collection db collection-name))]
    (mapv (fn [snap]
            (firestore->clj (.getData snap)))
          (.getDocuments results))))

(defn query-where
  "Query a collection with a where clause."
  [^Firestore db collection-name field op value]
  (inc-reads!)
  (let [col   (.collection db collection-name)
        q     (case op
                :!=             (.whereNotEqualTo col field value)
                :==             (.whereEqualTo col field value)
                :array-contains (.whereArrayContains col field value))
        results @(.get q)]
    (mapv (fn [snap]
            (firestore->clj (.getData snap)))
          (.getDocuments results))))

;; --- Init helpers ---

(defn init-meta!
  "Initialize meta documents if they don't exist."
  [^Firestore db]
  (let [video-ids-doc (get-doc db "meta/video_ids" false)]
    (when (or (nil? video-ids-doc) (nil? (:videoIds video-ids-doc)))
      (set-doc db "meta/video_ids" {:videoIds []} {:no-quota? true})))
  (let [state-doc (get-doc db "meta/state" false)]
    (when (nil? state-doc)
      (set-doc db "meta/state" {} {:no-quota? true})))
  ;; Verify writes work
  (set-doc db "meta/test" {})
  (log/info "Meta documents initialized"))
