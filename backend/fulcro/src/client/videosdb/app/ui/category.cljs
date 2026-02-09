(ns videosdb.app.ui.category
  "Category page (Explorer filtered). Replaces Category.vue."
  (:require [com.fulcrologic.fulcro.dom :as dom]
            [videosdb.app.ui.explorer :as explorer]))

(defn ui-category-page
  "Category page: renders Explorer filtered by a playlist.
   category should have :snippet.title and :id"
  [category]
  (when category
    (let [title (.. category -snippet -title)]
      (dom/div {:className "container p-0 m-0"}
        (dom/h1 {:className "text-center"} (str "Category: " title))
        (explorer/ui-explorer {:category {:id (.-id category)}})))))
