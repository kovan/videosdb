(ns videosdb.app.ui.home
  "Home page (Explorer). Replaces Home.vue."
  (:require [com.fulcrologic.fulcro.dom :as dom]
            [videosdb.app.ui.explorer :as explorer]))

(defn ui-home-page
  "Home page: renders the Explorer with no filters."
  []
  (dom/div {:className "container p-0 m-0"}
    (explorer/ui-explorer {})))
