
;; ============================================================================
;; src/videosdb/settings.clj - Configuration settings
;; ============================================================================

(ns videosdb.settings
  (:require [environ.core :refer [env]]
            [taoensso.timbre :as log]))

(def config
  {:ipfs-host (env :ipfs-host "127.0.0.1")
   :ipfs-port (Integer/parseInt (env :ipfs-port "5001"))
   :videosdb-domain "sadhguru.digital"
   :videosdb-dnszone "sadhguru"
   :youtube-channel {:id "UCcYzLCs3zrQIBVHYA1sK2sw" :name "Sadhguru"}
   :truncate-description-after "#Sadhguru"
   :video-files-dir "/mnt/videos"
   :youtube-key "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU"
   :youtube-key-testing "AIzaSyDM-rEutI1Mr6_b1Uz8tofj2dDlwcOzkjs"})

;; Logging setup
(log/set-config!
 {:level (keyword (env :loglevel "info"))
  :appenders {:console {:enabled? true
                        :fn (fn [data]
                              (println (str (:level data) "\t"
                                            (:instant data) ":"
                                            (:?ns-str data) "." (:?fn-str data)
                                            " (" (:?file data) ":" (:?line data) "): "
                                            (:msg_ data))))}}})