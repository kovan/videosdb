

;; ============================================================================
;; src/videosdb/utils.clj - Utility functions
;; ============================================================================

(ns videosdb.utils
  (:require [clojure.tools.logging :as log]
            [clojure.string :as str]
            [clojure.core.async :as async])
  (:import [java.net Socket SocketTimeoutException]
           [java.io IOException]
           [java.time Instant Duration]
           [java.time.format DateTimeFormatter]
           [java.util.concurrent.atomic AtomicInteger]))

;; Exception handling
(def quota-exceeded-type ::quota-exceeded)

(defn quota-exceeded [message]
  {::type quota-exceeded-type ::message message})

(defn quota-exceeded? [x]
  (= (::type x) quota-exceeded-type))

;; Network utilities
(defn wait-for-port
  ([port] (wait-for-port port "localhost" 30.0))
  ([port host] (wait-for-port port host 30.0))
  ([port host timeout]
   (log/debug (format "waiting for port %s:%s to be open" port host))
   (let [start-time (System/currentTimeMillis)]
     (loop []
       (try
         (let [socket (Socket. host port)]
           (.close socket)
           true)
         (catch IOException _
           (Thread/sleep 10)
           (when (< (- (System/currentTimeMillis) start-time) (* timeout 1000))
             (recur))))))))

;; Collection utilities
(defn put-item-at-front [seq item]
  (if (nil? item)
    seq
    (let [index (.indexOf (vec seq) item)]
      (if (>= index 0)
        (concat (drop index seq) (take index seq))
        seq))))

;; String utilities
(defn slugify [text]
  (when text
    (-> text
        str/lower-case
        (str/replace #"[^\w\s-]" "")
        (str/replace #"\s+" "-")
        (str/replace #"-+" "-")
        (str/replace #"^-|-$" ""))))

(defn parse-youtube-id [string]
  (when-let [match (re-find #"\[(.{11})\]\." string)]
    (second match)))

;; Time utilities
(defn parse-duration [duration-str]
  (when duration-str
    (try
      (let [duration (Duration/parse duration-str)]
        (.getSeconds duration))
      (catch Exception e
        (log/warn (format "Could not parse duration: %s" duration-str))
        0))))

(defn parse-datetime [datetime-str]
  (when datetime-str
    (try
      (Instant/parse datetime-str)
      (catch Exception e
        (log/warn (format "Could not parse datetime: %s" datetime-str))
        (Instant/now)))))

;; Error handling
(defn handle-exception [exception-type exception handler-fn]
  (if (and (map? exception) (= (::type exception) exception-type))
    (do (handler-fn exception) true)
    false))

;; Counter utilities
(defn create-counter [type limit]
  {:type type :counter (AtomicInteger. 0) :limit limit :lock (Object.)})

(defn inc-counter! [counter & [quantity]]
  (let [qty (or quantity 1)]
    (locking (:lock counter)
      (let [new-val (.addAndGet (:counter counter) qty)]
        (when (> new-val (:limit counter))
          (throw (ex-info "Counter limit exceeded"
                          (quota-exceeded (format "Surpassed %s ops limit of %s"
                                                  (:type counter) (:limit counter))))))))))

(defn counter-stats [counter]
  (format "Counter %s: %s/%s"
          (:type counter)
          (.get (:counter counter))
          (:limit counter)))