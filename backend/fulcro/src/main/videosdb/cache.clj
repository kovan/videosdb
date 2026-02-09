(ns videosdb.cache
  "Redis caching via Carmine. Replaces Cache class in youtube_api.py."
  (:require [taoensso.carmine :as car :refer [wcar]]
            [clojure.data.json :as json]
            [clojure.tools.logging :as log]
            [clojure.string :as str]))

(defn make-conn-opts
  "Create Carmine connection options."
  ([] (make-conn-opts nil))
  ([redis-db-n]
   {:pool {}
    :spec {:uri (or (System/getenv "REDIS_URL") "redis://localhost:6379")
           :db  (or redis-db-n 0)}}))

(defn key-func
  "Generate cache key from URL and params, matching Python logic.
   Excludes the 'key' param (API key) since it can vary."
  [url params]
  (let [sorted-params (->> (dissoc params "key" :key)
                           (sort-by (comp str key))
                           (map (fn [[k v]] (str (name k) "=" v)))
                           (str/join "&"))
        clean-url     (str/replace url #"^/" "")]
    (str clean-url "?" sorted-params)))

(defn- pages-key [base-key page-n]
  (str base-key "_page_" page-n))

(defn cache-get
  "Get cached response. Returns [etag pages-vec] or [nil nil]."
  [conn-opts cache-key]
  (let [value (wcar conn-opts (car/get cache-key))]
    (if (nil? value)
      [nil nil]
      (let [meta-data  (json/read-str value :key-fn keyword)
            page-count (:n_pages meta-data)
            pages      (vec
                        (for [n (range page-count)]
                          (let [page-str (wcar conn-opts
                                              (car/get (pages-key cache-key n)))]
                            (when page-str
                              (json/read-str page-str :key-fn keyword)))))]
        (if (some nil? pages)
          [nil nil]
          [(:etag meta-data) pages])))))

(defn cache-set
  "Store pages in cache. Returns the pages vector."
  [conn-opts cache-key pages]
  (let [page-count (count pages)
        etag       (get (first pages) :etag (get (first pages) "etag"))]
    (wcar conn-opts
          (doseq [n (range page-count)]
            (car/set (pages-key cache-key n)
                     (json/write-str (nth pages n))))
          (car/set cache-key
                   (json/write-str {:etag    etag
                                    :n_pages page-count})))
    pages))

(defn cache-stats
  "Get Redis statistics."
  [conn-opts]
  (let [info (wcar conn-opts (car/info "stats"))]
    info))
