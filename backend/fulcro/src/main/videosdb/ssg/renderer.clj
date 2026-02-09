(ns videosdb.ssg.renderer
  "Invokes Node SSR script per route. Produces HTML from Fulcro state."
  (:require [clojure.tools.logging :as log]
            [clojure.data.json :as json]
            [clojure.java.io :as io]
            [babashka.process :as proc]
            [clojure.string :as str]))

(defonce ^:private ssr-process (atom nil))

(defn- start-ssr-process!
  "Start the Node.js SSR process if not already running."
  []
  (when-not @ssr-process
    (log/info "Starting Node SSR process...")
    (let [p (proc/process ["node" "target/ssr.js"]
                          {:dir (System/getProperty "user.dir")
                           :in  :pipe
                           :out :pipe
                           :err :pipe})]
      (reset! ssr-process p)
      ;; Read initial ready message
      (let [reader (io/reader (:out p))
            first-line (.readLine reader)]
        (log/info "SSR process ready:" first-line))
      p)))

(defn- ensure-ssr! []
  (or @ssr-process (start-ssr-process!)))

(defn stop-ssr!
  "Stop the SSR Node process."
  []
  (when-let [p @ssr-process]
    (proc/destroy p)
    (reset! ssr-process nil)
    (log/info "SSR process stopped")))

(defn render-to-html
  "Render a route to HTML using the Node SSR process.
   Returns the HTML string for the page body."
  [route state app-config]
  (let [p      (ensure-ssr!)
        input  (json/write-str {:route  route
                                :state  state
                                :config app-config})
        writer (io/writer (:in p))
        reader (io/reader (:out p))]
    (.write writer input)
    (.write writer "\n")
    (.flush writer)
    ;; Read the response (single JSON line)
    (let [response-line (.readLine reader)]
      (when response-line
        (let [response (json/read-str response-line :key-fn keyword)]
          (:html response))))))

(defn wrap-html
  "Wrap rendered body HTML in a full HTML document."
  [{:keys [title description canonical body state app-config]}]
  (let [state-json (json/write-str (or state {}))]
    (str "<!DOCTYPE html>\n"
         "<html lang=\"en\">\n"
         "<head>\n"
         "  <meta charset=\"utf-8\">\n"
         "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
         "  <meta http-equiv=\"content-language\" content=\"en\">\n"
         (when title
           (str "  <title>" title "</title>\n"))
         (when description
           (str "  <meta name=\"description\" content=\""
                (str/replace (or description "") "\"" "&quot;")
                "\">\n"))
         (when canonical
           (str "  <link rel=\"canonical\" href=\"" canonical "\">\n"))
         "  <link rel=\"icon\" type=\"image/x-icon\" href=\"/favicon.ico\">\n"
         "  <link rel=\"stylesheet\" href=\"/css/bootstrap.min.css\">\n"
         "</head>\n"
         "<body>\n"
         "  <div id=\"app\">" (or body "") "</div>\n"
         "  <script>window.__FULCRO_INITIAL_STATE__ = " state-json ";</script>\n"
         ;; Inject app config globals
         "  <script>\n"
         (when (:title app-config)
           (str "    window.VIDEOSDB_TITLE = " (json/write-str (:title app-config)) ";\n"))
         (when (:subtitle app-config)
           (str "    window.VIDEOSDB_SUBTITLE = " (json/write-str (:subtitle app-config)) ";\n"))
         (when (:hostname app-config)
           (str "    window.VIDEOSDB_HOSTNAME = " (json/write-str (:hostname app-config)) ";\n"))
         (when (:website app-config)
           (str "    window.VIDEOSDB_WEBSITE = " (json/write-str (:website app-config)) ";\n"))
         (when (:config app-config)
           (str "    window.VIDEOSDB_CONFIG = " (json/write-str (:config app-config)) ";\n"))
         (when (:cse-url app-config)
           (str "    window.VIDEOSDB_CSE_URL = " (json/write-str (:cse-url app-config)) ";\n"))
         "  </script>\n"
         "  <script src=\"/js/compiled/main.js\"></script>\n"
         "</body>\n"
         "</html>\n")))
