
;; ============================================================================
;; src/videosdb/ipfs.clj - IPFS integration (Functional)
;; ============================================================================

(ns videosdb.ipfs
  (:require [clojure.tools.logging :as log]
            [clojure.java.io :as io]
            [clojure.java.shell :as shell]
            [videosdb.settings :as settings]
            [videosdb.utils :as utils]
            [videosdb.db :as db])
  (:import [java.net InetAddress]
           [java.io File]))

;; DNS operations
(defn update-dns-record [dns-zone record-name record-type ttl new-value]
  (when dns-zone
    (log/info (format "Would update DNS record %s.%s %s %d %s"
                      record-name dns-zone record-type ttl new-value))))

(defn update-dnslink [dns-zone record-name new-root-hash]
  (update-dns-record dns-zone record-name "TXT" 300 (str "dnslink=/ipfs/" new-root-hash)))

(defn update-ip [dns-zone record-name new-ip]
  (update-dns-record dns-zone record-name "A" 300 new-ip))

;; IPFS operations
(defn create-ipfs-client [& [files-root]]
  {:files-root (or files-root "/videos")
   :host (.getHostAddress (InetAddress/getByName (:ipfs-host settings/config)))
   :port (:ipfs-port settings/config)
   :dnslink-update-pending (atom false)})
(defn add-to-ipfs-dir [ipfs-client filename hash]
  (let [src (str "/ipfs/" hash)
        dst (str (:files-root ipfs-client) "/" (.getName (File. filename)))]
    (log/info (format "Would copy %s to %s in IPFS MFS" src dst))
    (reset! (:dnslink-update-pending ipfs-client) true)))

(defn add-file-to-ipfs [ipfs-client filename & [add-to-dir? options]]
  (let [add-to-dir? (if (nil? add-to-dir?) true add-to-dir?)
        mock-hash "QmMockHashForFile123456789"]
    (log/info (format "Would add file %s to IPFS" filename))
    (when add-to-dir?
      (add-to-ipfs-dir ipfs-client filename mock-hash))
    mock-hash))



(defn get-file-from-ipfs [ipfs-client ipfs-hash]
  (log/info (format "Would get file with hash %s from IPFS" ipfs-hash))
  "mock-filename.mp4")

(defn update-ipfs-dnslink [ipfs-client & [force?]]
  (when (or @(:dnslink-update-pending ipfs-client) force?)
    (let [root-hash "QmMockRootHash123456789"]
      (update-dnslink (:videosdb-dnszone settings/config)
                      (str "videos." (:videosdb-domain settings/config))
                      root-hash)
      (reset! (:dnslink-update-pending ipfs-client) false))))

(defn list-files-in-ipfs [ipfs-client]
  "Returns map of youtube-id -> file info"
  {})

(defn list-files-in-disk [dir]
  (let [dir-file (File. dir)]
    (when (.exists dir-file)
      (->> (.listFiles dir-file)
           (filter #(.isFile %))
           (filter #(not (.endsWith (.getName %) ".part")))
           (map (fn [file]
                  (when-let [youtube-id (utils/parse-youtube-id (.getName file))]
                    [youtube-id (.getName file)])))
           (filter identity)
           (into {})))))

(defn download-and-register-folder [db-state ipfs-client & [overwrite-hashes?]]
  (log/info "Would download videos and register with IPFS")
  (let [videos-dir (.getAbsolutePath (File. (:video-files-dir settings/config)))]
    (when-not (.exists (File. videos-dir))
      (.mkdirs (File. videos-dir)))

    (let [files-in-ipfs (list-files-in-ipfs ipfs-client)
          files-in-disk (list-files-in-disk videos-dir)]
      (log/info (format "Found %d files in disk, %d in IPFS"
                        (count files-in-disk) (count files-in-ipfs)))

      ;; Process videos from database
      (let [video-ids-doc (db/db-get-noquota db-state "meta/video_ids")
            video-ids (when (.exists video-ids-doc)
                        (get (.getData video-ids-doc) "videoIds" []))]

        (doseq [video-id video-ids]
          (let [video-doc (db/db-get-noquota db-state (str "videos/" video-id))]
            (when (.exists video-doc)
              (let [video-data (.getData video-doc)]
                (when-not (contains? files-in-disk video-id)
                  (log/debug "Would download video:" video-id))

                (when-not (contains? files-in-ipfs video-id)
                  (log/debug "Would add to IPFS:" video-id)
                  (let [filename (str video-id ".mp4")
                        ipfs-hash (add-file-to-ipfs ipfs-client filename true)]
                    (db/db-set! db-state (str "videos/" video-id)
                                (assoc-in video-data [:videosdb :ipfs_hash] ipfs-hash)
                                true)))))))

        (update-ipfs-dnslink ipfs-client)))))
