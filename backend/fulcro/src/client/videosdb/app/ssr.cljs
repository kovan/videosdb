(ns videosdb.app.ssr
  "Node.js SSR script entry point. Reads route+state from stdin, outputs HTML."
  (:require ["react-dom/server" :as rdom]
            ["react" :as react]
            [com.fulcrologic.fulcro.dom.server :as dom]
            [com.fulcrologic.fulcro.components :as comp]
            [clojure.string :as str]))

;; For SSR, we render a minimal version of the page
;; The full Fulcro app hydrates on the client

(defn render-page
  "Render a page to HTML string given route and config."
  [route config]
  (let [title    (or (:title config) "VideosDB")
        subtitle (or (:subtitle config) "")]
    ;; Minimal server render - just the app shell
    ;; The client will hydrate with full data
    (rdom/renderToString
     (react/createElement "div" nil
       ;; Navbar
       (react/createElement "nav"
         #js {:className "navbar navbar-dark bg-dark p-2 pl-3 d-flex align-middle justify-content-end"}
         (react/createElement "a"
           #js {:className "mr-auto h5 mt-1 text-white align-middle text-decoration-none"
                :href "/"}
           title))
       ;; Subtitle
       (react/createElement "div"
         #js {:className "p-1 px-2 mt-2 text-center"}
         (react/createElement "strong" nil subtitle))
       ;; Content placeholder
       (react/createElement "div"
         #js {:className "container"}
         (react/createElement "div"
           #js {:className "row"}
           (react/createElement "main"
             #js {:className "col-md-12 col-lg-12 ml-sm-auto px-md-4 pt-4"
                  :role "main"}
             ;; Loading placeholder
             (react/createElement "div"
               #js {:className "text-center p-4"}
               (react/createElement "div"
                 #js {:className "spinner-border text-primary"
                      :role "status"}
                 (react/createElement "span"
                   #js {:className "sr-only"}
                   "Loading..."))))))))))

(defn ^:export main
  "Main SSR entry point. Reads JSON lines from stdin, writes HTML responses."
  []
  (js/console.log "SSR process ready")
  (let [readline (js/require "readline")
        rl       (.createInterface readline
                   #js {:input  js/process.stdin
                        :output js/process.stdout
                        :terminal false})]
    (.on rl "line"
      (fn [line]
        (try
          (let [input  (js/JSON.parse line)
                route  (.-route input)
                config (js->clj (.-config input) :keywordize-keys true)
                html   (render-page route config)]
            (js/process.stdout.write
             (str (js/JSON.stringify #js {:html html}) "\n")))
          (catch :default e
            (js/console.error "SSR error:" e)
            (js/process.stdout.write
             (str (js/JSON.stringify #js {:html "" :error (str e)}) "\n"))))))))
