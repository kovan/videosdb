(ns videosdb.cli
  "CLI entry point. Replaces run.py."
  (:require [clojure.tools.cli :refer [parse-opts]]
            [clojure.tools.logging :as log]
            [videosdb.downloader :as downloader]
            [videosdb.ssg.generator :as generator])
  (:gen-class))

(def cli-options
  [["-c" "--check-for-new-videos" "Sync YouTube data to Firestore"]
   ["-g" "--generate" "Generate static site"]
   ["-v" "--dotenv FILE" "Load environment from file"]
   ["-h" "--help" "Show help"]])

(defn- load-dotenv
  "Load environment variables from a file (KEY=VALUE format)."
  [path]
  (doseq [line (clojure.string/split-lines (slurp path))]
    (let [line (clojure.string/trim line)]
      (when (and (seq line) (not (.startsWith line "#")))
        (let [[k v] (clojure.string/split line #"=" 2)]
          (when (and k v)
            ;; Java doesn't allow setting env vars at runtime easily,
            ;; so we set system properties as fallback
            (System/setProperty (clojure.string/trim k)
                                (clojure.string/trim v))))))))

(defn -main [& args]
  (let [{:keys [options errors summary]} (parse-opts args cli-options)]
    (when (:help options)
      (println summary)
      (System/exit 0))

    (when errors
      (doseq [e errors] (println "Error:" e))
      (System/exit 1))

    (when (:dotenv options)
      (load-dotenv (:dotenv options)))

    (when (:check-for-new-videos options)
      (log/info "Starting sync...")
      (downloader/check-for-new-videos))

    (when (:generate options)
      (log/info "Starting static site generation...")
      (generator/generate))))
