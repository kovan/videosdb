(ns videosdb.app.ui.search
  "Google CSE search page. Replaces search.vue."
  (:require [com.fulcrologic.fulcro.dom :as dom]))

(defonce ^:private script-loaded? (atom false))

(defn- load-cse-script! []
  (when-not @script-loaded?
    (when-let [cse-url js/goog.global.VIDEOSDB_CSE_URL]
      (let [script (.createElement js/document "script")]
        (set! (.-src script) cse-url)
        (set! (.-async script) true)
        (.appendChild (.-head js/document) script)
        (reset! script-loaded? true)))))

(defn ui-search-page
  "Search page with Google Custom Search Engine."
  []
  (load-cse-script!)
  (dom/div nil
    (dom/h2 {:className "text-center"} "Search")
    (dom/div {:className "gcse-search"})))
