(ns videosdb.app.firebase
  "Firebase JS Lite SDK wrapper for client-side Firestore queries."
  (:require ["firebase/app" :refer [initializeApp getApp]]
            ["firebase/firestore/lite" :as fsl
             :refer [getFirestore getDoc getDocs doc collection
                     query where orderBy limit startAfter
                     connectFirestoreEmulator]]))

(defonce ^:private db-instance (atom nil))
(defonce ^:private app-instance (atom nil))

;; Firebase configs for each deployment
(def firebase-configs
  {"sadhguru"    {:apiKey            "AIzaSyAhKg1pGeJnL_ZyD1wv7ZPXwfZ6_7OBRa8"
                  :authDomain        "videosdb-firebase.firebaseapp.com"
                  :projectId         "videosdb-firebase"
                  :storageBucket     "videosdb-firebase.appspot.com"
                  :messagingSenderId "136865344383"
                  :appId             "1:136865344383:web:2d9764597f98be41c7884a"}
   "nithyananda" {:apiKey            "AIzaSyAokazNFM0aCatQ2HLQI2EmsL_fJvTUWyQ"
                  :authDomain        "videosdb-nithyananda.firebaseapp.com"
                  :projectId         "videosdb-nithyananda"
                  :storageBucket     "videosdb-nithyananda.appspot.com"
                  :messagingSenderId "550038984532"
                  :appId             "1:550038984532:web:c69ab834dc3da08481dac1"}
   "testing"     {:apiKey            "AIzaSyB4ssPNsGaIpFv8GNiBl-MbRWzRbuYV-MM"
                  :authDomain        "videosdb-testing.firebaseapp.com"
                  :projectId         "videosdb-testing"
                  :storageBucket     "videosdb-testing.appspot.com"
                  :messagingSenderId "224322811272"
                  :appId             "1:224322811272:web:82113e7ad6fa250915763d"}})

(defn get-config []
  (let [config-name (or (js* "window[\"VIDEOSDB_CONFIG\"]") "testing")]
    (get firebase-configs config-name)))

(defn init-db!
  "Initialize Firebase and return the Firestore instance."
  []
  (if @db-instance
    @db-instance
    (let [config     (get-config)
          emulator   (js* "window[\"FIRESTORE_EMULATOR_HOST\"]")
          config     (if emulator
                       (assoc config :projectId "demo-project")
                       config)
          app        (initializeApp (clj->js config))
          db         (getFirestore app)]
      (when emulator
        (let [[host port] (.split emulator ":")]
          (connectFirestoreEmulator db host (js/parseInt port))))
      (reset! app-instance app)
      (reset! db-instance db)
      db)))

(defn get-db []
  (or @db-instance (init-db!)))

;; --- Query helpers ---

(defn query-videos-page
  "Query videos collection with ordering, filtering, pagination.
   Returns a promise resolving to {:docs [...] :cursor last-doc}."
  [{:keys [order-field order-dir category-id tag cursor page-size]
    :or   {order-field "snippet.publishedAt"
           order-dir   "desc"
           page-size   20}}]
  (let [db    (get-db)
        col   (collection db "videos")
        constraints (cond-> [(orderBy order-field order-dir)]
                      category-id
                      (conj (where "videosdb.playlists" "array-contains" category-id))

                      tag
                      (conj (where "snippet.tags" "array-contains" tag))

                      cursor
                      (conj (startAfter cursor))

                      true
                      (conj (limit page-size)))
        q     (apply query col (clj->js constraints))]
    (-> (getDocs q)
        (.then (fn [snapshot]
                 (let [docs (array-seq (unchecked-get snapshot "docs"))]
                   {:docs   (mapv (fn [d]
                                    (let [data (js->clj (js/JSON.parse (js/JSON.stringify (.data d)))
                                                        :keywordize-keys true)]
                                      (assoc data :id (unchecked-get d "id"))))
                                  docs)
                    :cursor (last docs)
                    :count  (count docs)}))))))

(defn get-doc-by-path
  "Get a single document by path. Returns a promise."
  [path]
  (let [db (get-db)]
    (-> (getDoc (doc db path))
        (.then (fn [snap]
                 (when (.exists snap)
                   (js/JSON.parse (js/JSON.stringify (.data snap)))))))))

(defn query-by-field
  "Query a collection where field == value. Returns promise of first doc data."
  [collection-name field value]
  (let [db  (get-db)
        col (collection db collection-name)
        q   (query col (where field "==" value))]
    (-> (getDocs q)
        (.then (fn [snapshot]
                 (let [docs (array-seq (unchecked-get snapshot "docs"))]
                   (when (seq docs)
                     (js/JSON.parse (js/JSON.stringify (.data (first docs)))))))))))

(defn get-all-playlists
  "Get all playlists ordered by lastUpdated desc. Returns promise."
  []
  (let [db  (get-db)
        col (collection db "playlists")
        q   (query col (orderBy "videosdb.lastUpdated" "desc"))]
    (-> (getDocs q)
        (.then (fn [snapshot]
                 (mapv (fn [d]
                         (let [data (js->clj (js/JSON.parse (js/JSON.stringify (.data d)))
                                             :keywordize-keys true)]
                           (let [last-upd (get-in data [:videosdb :lastUpdated])]
                             {:name         (get-in data [:snippet :title])
                              :slug         (get-in data [:videosdb :slug])
                              :use_count    (get-in data [:videosdb :videoCount])
                              :last_updated (if (and (map? last-upd) (:seconds last-upd))
                                              (:seconds last-upd)
                                              last-upd)
                              :id           (unchecked-get d "id")})))
                       (array-seq (unchecked-get snapshot "docs"))))))))

(defn get-random-video-slug
  "Get a random video slug from meta/video_ids. Returns promise of slug string."
  []
  (-> (get-doc-by-path "meta/video_ids")
      (.then (fn [data]
               (let [ids (unchecked-get data "videoIds")
                     vid (aget ids (js/Math.floor (* (js/Math.random) (alength ids))))]
                 (-> (get-doc-by-path (str "videos/" vid))
                     (.then (fn [vdata]
                              (when vdata
                                (unchecked-get (unchecked-get vdata "videosdb") "slug"))))))))))
