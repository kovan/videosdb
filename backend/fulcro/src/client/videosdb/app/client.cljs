(ns videosdb.app.client
  "Fulcro app initialization + hydration."
  (:require [com.fulcrologic.fulcro.application :as app]
            [com.fulcrologic.fulcro.components :as comp]
            [com.fulcrologic.fulcro.routing.dynamic-routing :as dr]
            [videosdb.app.ui.root :as root]
            [videosdb.app.firebase :as fb]))

(defonce APP (app/fulcro-app {}))

(defn ^:export init
  "Initialize the Fulcro application."
  []
  ;; Initialize Firebase
  (fb/init-db!)

  ;; Check for pre-rendered state (SSG hydration)
  (when-let [initial-state js/window.__FULCRO_INITIAL_STATE__]
    (let [state (js->clj initial-state :keywordize-keys true)]
      (reset! (::app/state-atom APP) state)))

  ;; Mount the app
  (app/mount! APP root/Root "app")

  ;; Initialize routing
  (dr/initialize! APP))

(defn ^:export refresh
  "Hot reload entry point."
  []
  (app/mount! APP root/Root "app"))
