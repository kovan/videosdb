(ns videosdb.ssg.generator
  "Static site generation orchestrator. Replaces mymodule.js."
  (:require [clojure.tools.logging :as log]
            [clojure.java.io :as io]
            [clojure.data.json :as json]
            [clojure.string :as str]
            [videosdb.config :as config]
            [videosdb.firestore :as fs]
            [videosdb.server.pathom :as pathom]
            [videosdb.ssg.renderer :as renderer]
            [videosdb.app.model :as model]
            [videosdb.util :as util]))

(def ^:private dist-dir "dist")

;; --- Route discovery ---

(defn- discover-routes
  "Discover all routes that need static HTML generation."
  [db]
  (log/info "Discovering routes...")
  (let [videos    (fs/query-where db "videos" "videosdb.slug" :!= "")
        playlists (fs/query-collection db "playlists")]

    (log/info "Found" (count videos) "videos and" (count playlists) "playlists")

    (concat
     ;; Home page
     [{:route "/"
       :type  :home}]

     ;; Video pages
     (->> videos
          (filter #(seq (get-in % [:videosdb :slug])))
          (map (fn [v]
                 {:route (str "/video/" (get-in v [:videosdb :slug]))
                  :type  :video
                  :data  v})))

     ;; Category pages
     (->> playlists
          (filter #(seq (get-in % [:videosdb :slug])))
          (map (fn [p]
                 {:route (str "/category/" (get-in p [:videosdb :slug]))
                  :type  :category
                  :data  p}))))))

;; --- HTML generation ---

(defn- generate-page!
  "Generate a single HTML page and write to dist."
  [route-info app-config]
  (let [{:keys [route type data]} route-info
        path     (if (= "/" route)
                   (str dist-dir "/index.html")
                   (str dist-dir route "/index.html"))
        dir      (io/file (.getParent (io/file path)))
        title    (case type
                   :home     (:title app-config)
                   :video    (str (get-in data [:snippet :title]) " - " (:subtitle app-config))
                   :category (str (get-in data [:snippet :title]) " - " (:title app-config))
                   (:title app-config))
        desc     (case type
                   :home     (:subtitle app-config)
                   :video    (get-in data [:snippet :description])
                   :category (str "Category: " (get-in data [:snippet :title]))
                   (:subtitle app-config))
        canon    (when (:hostname app-config)
                   (str (:hostname app-config) route))]

    (.mkdirs dir)

    ;; For now, generate HTML without SSR (placeholder body)
    ;; The client JS will hydrate and render the full content
    (let [html (renderer/wrap-html
                {:title      title
                 :description desc
                 :canonical  canon
                 :body       ""
                 :state      {}
                 :app-config app-config})]
      (spit path html))

    (log/debug "Generated:" path)))

;; --- Sitemap generation ---

(defn- video-to-sitemap-entry [video hostname]
  (let [snippet  (:snippet video)
        videosdb (:videosdb video)]
    (str "  <url>\n"
         "    <loc>" hostname "/video/" (:slug videosdb) "</loc>\n"
         "    <priority>1.0</priority>\n"
         "    <video:video>\n"
         "      <video:thumbnail_loc>" (get-in snippet [:thumbnails :medium :url]) "</video:thumbnail_loc>\n"
         "      <video:title>" (str/escape (or (:title snippet) "") {\< "&lt;" \> "&gt;" \& "&amp;"}) "</video:title>\n"
         "      <video:description>" (str/escape (or (:title snippet) "") {\< "&lt;" \> "&gt;" \& "&amp;"}) "</video:description>\n"
         (when (:durationSeconds videosdb)
           (str "      <video:duration>" (int (:durationSeconds videosdb)) "</video:duration>\n"))
         (when (:publishedAt snippet)
           (str "      <video:publication_date>" (util/date-to-iso (:publishedAt snippet)) "</video:publication_date>\n"))
         "      <video:player_loc>https://www.youtube.com/watch?v=" (:id video) "</video:player_loc>\n"
         "    </video:video>\n"
         "  </url>\n")))

(defn- generate-sitemap!
  "Generate sitemap.xml."
  [routes hostname]
  (log/info "Generating sitemap.xml...")
  (let [path (str dist-dir "/sitemap.xml")
        xml  (str "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                  "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"\n"
                  "        xmlns:video=\"http://www.google.com/schemas/sitemap-video/1.1\">\n"
                  "  <url>\n"
                  "    <loc>" hostname "/</loc>\n"
                  "    <changefreq>daily</changefreq>\n"
                  "  </url>\n"
                  (->> routes
                       (filter #(= :video (:type %)))
                       (map #(video-to-sitemap-entry (:data %) hostname))
                       (str/join))
                  (->> routes
                       (filter #(= :category (:type %)))
                       (map (fn [r]
                              (str "  <url>\n"
                                   "    <loc>" hostname (:route r) "</loc>\n"
                                   "    <priority>0.1</priority>\n"
                                   "  </url>\n")))
                       (str/join))
                  "</urlset>\n")]
    (spit path xml)
    (log/info "Generated sitemap.xml")))

;; --- Robots.txt ---

(defn- generate-robots-txt! [hostname]
  (let [path (str dist-dir "/robots.txt")
        content (str "User-agent: *\n"
                     "Allow: /\n\n"
                     "Sitemap: " hostname "/sitemap.xml\n")]
    (spit path content)
    (log/info "Generated robots.txt")))

;; --- Static assets ---

(defn- copy-static-assets!
  "Copy static assets from resources/public to dist."
  []
  (log/info "Copying static assets...")
  (let [src-dir (io/file "resources/public")]
    (when (.exists src-dir)
      (doseq [f (file-seq src-dir)]
        (when (.isFile f)
          (let [rel-path (.relativize (.toPath src-dir) (.toPath f))
                dest     (io/file dist-dir (str rel-path))]
            (.mkdirs (.getParentFile dest))
            (io/copy f dest)))))))

;; --- Main generate function ---

(defn generate
  "Run the full static site generation pipeline."
  []
  (log/info "Starting static site generation...")
  (let [cfg        (config/config)
        app-config {:title    (:title cfg)
                    :subtitle (:subtitle cfg)
                    :hostname (:hostname cfg)
                    :website  (:website cfg)
                    :config   (:videosdb-config cfg)
                    :cse-url  (:cse-url cfg)}
        hostname   (or (:hostname cfg) "")
        db         (fs/create-client)]

    ;; Create dist directory
    (.mkdirs (io/file dist-dir))

    ;; Discover routes
    (let [routes (discover-routes db)]
      (log/info "Generating" (count routes) "pages...")

      ;; Generate each page
      (doseq [route-info routes]
        (try
          (generate-page! route-info app-config)
          (catch Exception e
            (log/error e "Failed to generate:" (:route route-info)))))

      ;; Generate sitemap and robots.txt
      (generate-sitemap! routes hostname)
      (generate-robots-txt! hostname))

    ;; Copy static assets
    (copy-static-assets!)

    ;; Generate fallback index.html for SPA routes (tags, etc.)
    (generate-page! {:route "/" :type :home} app-config)

    (log/info "Static site generation complete. Output:" dist-dir)))
