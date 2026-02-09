(ns videosdb.app.routing
  "Fulcro dynamic router definitions."
  (:require [com.fulcrologic.fulcro.routing.dynamic-routing :as dr :refer [defrouter]]
            [com.fulcrologic.fulcro.components :as comp :refer [defsc]]))

;; Forward declarations of page components (defined in UI ns)
(defsc HomePage [_ _]
  {:ident         (fn [] [:component/id :home])
   :query         []
   :route-segment [""]
   :initial-state {}})

(defsc VideoPage [_ _]
  {:ident         (fn [] [:component/id :video])
   :query         [:video/slug]
   :route-segment ["video" :video/slug]
   :initial-state {}})

(defsc CategoryPage [_ _]
  {:ident         (fn [] [:component/id :category])
   :query         [:playlist/slug]
   :route-segment ["category" :playlist/slug]
   :initial-state {}})

(defsc TagPage [_ _]
  {:ident         (fn [] [:component/id :tag])
   :query         [:tag/slug]
   :route-segment ["tag" :tag/slug]
   :initial-state {}})

(defsc SearchPage [_ _]
  {:ident         (fn [] [:component/id :search])
   :query         []
   :route-segment ["search"]
   :initial-state {}})

(defrouter MainRouter [_ _]
  {:router-targets [HomePage VideoPage CategoryPage TagPage SearchPage]})

(def ui-main-router (comp/factory MainRouter))
