(ns videosdb.app.ui.tag
  "Tag page (Explorer filtered). Replaces Tag.vue."
  (:require [com.fulcrologic.fulcro.dom :as dom]
            [videosdb.app.ui.explorer :as explorer]))

(defn ui-tag-page
  "Tag page: renders Explorer filtered by a tag."
  [tag-slug]
  (dom/div {:className "container p-0 m-0"}
    (dom/h1 {:className "text-center"} (str "Tag: " tag-slug))
    (explorer/ui-explorer {:tag tag-slug})))
