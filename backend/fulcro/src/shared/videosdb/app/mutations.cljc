(ns videosdb.app.mutations
  "Fulcro mutations."
  (:require [com.fulcrologic.fulcro.mutations :as m :refer [defmutation]]
            [com.fulcrologic.fulcro.algorithms.merge :as merge]))

(defmutation set-categories
  "Set the categories list in the app state."
  [{:keys [categories]}]
  (action [{:keys [state]}]
    (swap! state assoc :app/categories categories)))

(defmutation set-videos
  "Append videos to the explorer state."
  [{:keys [videos]}]
  (action [{:keys [state]}]
    (swap! state update :explorer/videos
           (fnil into {})
           (map (fn [v] [(:video/id v) v]) videos))))

(defmutation clear-videos
  "Clear the explorer video list (on ordering change)."
  [_]
  (action [{:keys [state]}]
    (swap! state assoc :explorer/videos {}
                       :explorer/cursor nil
                       :explorer/no-more? false)))

(defmutation set-explorer-cursor
  "Set the pagination cursor for the explorer."
  [{:keys [cursor no-more?]}]
  (action [{:keys [state]}]
    (swap! state assoc :explorer/cursor cursor
                       :explorer/no-more? (boolean no-more?))))

(defmutation set-current-video
  "Set the currently displayed video."
  [{:keys [video]}]
  (action [{:keys [state]}]
    (swap! state assoc :app/current-video video)))

(defmutation set-current-category
  "Set the currently displayed category."
  [{:keys [category]}]
  (action [{:keys [state]}]
    (swap! state assoc :app/current-category category)))

(defmutation toggle-sidebar
  "Toggle the sidebar visibility."
  [_]
  (action [{:keys [state]}]
    (swap! state update :app/sidebar-visible? not)))

(defmutation set-sidebar-visible
  "Set sidebar visibility."
  [{:keys [visible?]}]
  (action [{:keys [state]}]
    (swap! state assoc :app/sidebar-visible? visible?)))
