(ns videosdb.app.ui.loading
  "Loading spinner component."
  (:require [com.fulcrologic.fulcro.dom :as dom]))

(defn ui-loading
  "A CSS-only loading spinner."
  []
  (dom/div {:className "text-center p-4"}
    (dom/div {:className "spinner-border text-primary"
              :role      "status"}
      (dom/span {:className "sr-only"} "Loading..."))))
