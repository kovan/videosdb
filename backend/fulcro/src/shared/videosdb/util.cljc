(ns videosdb.util
  "Shared utilities: date formatting, slug helpers."
  #?(:cljs (:require [goog.string :as gstr]
                     [goog.string.format])))

(defn format-duration
  "Format duration in seconds to HH:MM:SS string."
  [seconds]
  (when seconds
    (let [s  (int seconds)
          h  (quot s 3600)
          m  (quot (mod s 3600) 60)
          ss (mod s 60)]
      #?(:clj  (format "%02d:%02d:%02d" h m ss)
         :cljs (gstr/format "%02d:%02d:%02d" h m ss)))))

(defn format-date
  "Format a date for display."
  [date]
  #?(:clj
     (when date
       (cond
         (instance? java.util.Date date)
         (let [fmt (java.text.SimpleDateFormat. "EEEE, MMMM d, yyyy")]
           (.format fmt date))

         (string? date)
         date

         :else (str date)))

     :cljs
     (when date
       (cond
         (instance? js/Date date)
         (.toLocaleDateString date js/undefined
                              #js {:weekday "long" :year "numeric"
                                   :month "long" :day "numeric"})

         (and (object? date) (.-seconds date))
         (let [d (js/Date. (* (.-seconds date) 1000))]
           (.toLocaleDateString d js/undefined
                                #js {:weekday "long" :year "numeric"
                                     :month "long" :day "numeric"}))

         (string? date)
         (let [d (js/Date. date)]
           (.toLocaleDateString d js/undefined
                                #js {:weekday "long" :year "numeric"
                                     :month "long" :day "numeric"}))

         :else (str date)))))

(defn date-to-iso
  "Convert a date to ISO string."
  [date]
  #?(:clj
     (when date
       (cond
         (instance? java.util.Date date)
         (.format (java.text.SimpleDateFormat. "yyyy-MM-dd'T'HH:mm:ss'Z'") date)

         (string? date) date
         :else (str date)))

     :cljs
     (when date
       (cond
         (string? date) date
         (instance? js/Date date) (.toISOString date)
         (and (object? date) (.-seconds date))
         (.toISOString (js/Date. (* (.-seconds date) 1000)))
         :else (str date)))))

(defn slugify
  "Generate URL-friendly slug."
  [s]
  (when s
    (-> s
        #?(:clj  clojure.string/lower-case
           :cljs clojure.string/lower-case)
        (clojure.string/replace #"[^\p{L}\p{N}\s-]" "")
        clojure.string/trim
        (clojure.string/replace #"[\s]+" "-")
        (clojure.string/replace #"-+" "-")
        (clojure.string/replace #"^-|-$" ""))))
