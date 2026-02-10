(ns videosdb.app.ui.root
  "Root layout: navbar, sidebar, footer. Replaces default.vue."
  (:require [com.fulcrologic.fulcro.dom :as dom]
            [com.fulcrologic.fulcro.components :as comp :refer [defsc]]
            [videosdb.app.firebase :as fb]
            [videosdb.app.ui.home :as home]
            [videosdb.app.ui.video :as video]
            [videosdb.app.ui.category :as category]
            [videosdb.app.ui.tag :as tag]
            [videosdb.app.ui.search :as search]
            [videosdb.app.ui.explorer :as explorer]
            [clojure.string :as str]))

;; --- App config from window globals ---
(defn- get-app-config []
  {:title    (or (js* "window[\"VIDEOSDB_TITLE\"]") "VideosDB")
   :subtitle (or (js* "window[\"VIDEOSDB_SUBTITLE\"]") "")
   :hostname (or (js* "window[\"VIDEOSDB_HOSTNAME\"]") "")
   :website  (or (js* "window[\"VIDEOSDB_WEBSITE\"]") "")
   :config   (or (js* "window[\"VIDEOSDB_CONFIG\"]") "testing")})

;; --- Sidebar state ---
(defonce sidebar-state
  (atom {:visible?    false
         :categories  []
         :ordering    "last_updated"
         :loaded?     false}))

(defn- load-categories! []
  (when-not (:loaded? @sidebar-state)
    (-> (fb/get-all-playlists)
        (.then (fn [cats]
                 (swap! sidebar-state assoc
                        :categories (vec cats)
                        :loaded? true))))))

(defn- sort-categories [categories ordering]
  (case ordering
    "name"         (sort-by :name categories)
    "use_count"    (reverse (sort-by :use_count categories))
    "last_updated" (reverse (sort-by (fn [c] (or (:last_updated c) 0)) categories))
    categories))

;; --- Client-side routing ---
(defonce current-route (atom {:page :home :params {}}))

(defn- parse-route
  "Parse the current URL path into a route map."
  [path]
  (let [parts (remove empty? (str/split path #"/"))]
    (cond
      (empty? parts)                          {:page :home :params {}}
      (= "video" (first parts))              {:page :video :params {:slug (second parts)}}
      (= "category" (first parts))           {:page :category :params {:slug (second parts)}}
      (= "tag" (first parts))                {:page :tag :params {:slug (js/decodeURIComponent (or (second parts) ""))}}
      (= "search" (first parts))             {:page :search :params {}}
      :else                                   {:page :home :params {}})))

(defn- navigate! [path]
  (when (not= path (.-pathname js/location))
    (.pushState js/history nil "" path))
  (reset! current-route (parse-route path)))

;; --- Page state for async data loading ---
(defonce page-data (atom {}))

(defn- load-video-page! [slug]
  (swap! page-data dissoc :video :video-playlists)
  (-> (fb/query-by-field "videos" "videosdb.slug" slug)
      (.then (fn [video-data]
               (swap! page-data assoc :video video-data)
               ;; Load playlists for this video
               (when-let [playlist-ids (and video-data
                                            (unchecked-get (unchecked-get video-data "videosdb") "playlists"))]
                 (let [ids (array-seq playlist-ids)]
                   (-> (js/Promise.all
                        (clj->js (map #(fb/get-doc-by-path (str "playlists/" %)) ids)))
                       (.then (fn [results]
                                (swap! page-data assoc
                                       :video-playlists
                                       (filterv some? (array-seq results))))))))))))

(defn- load-category-page! [slug]
  (swap! page-data dissoc :category)
  (-> (fb/query-by-field "playlists" "videosdb.slug" slug)
      (.then (fn [cat-data]
               (swap! page-data assoc :category cat-data)))))

;; --- Random video ---
(defn- random-video! []
  (-> (fb/get-random-video-slug)
      (.then (fn [slug]
               (when slug
                 (navigate! (str "/video/" slug)))))))

;; --- Navbar ---
(defn- ui-navbar [config]
  (dom/nav {:className "navbar navbar-dark bg-dark p-2 pl-3 d-flex align-middle justify-content-end"}
    (dom/a {:className "mr-auto h5 mt-1 text-white align-middle text-decoration-none"
            :href      "/"
            :onClick   (fn [e] (.preventDefault e) (navigate! "/"))}
      (str (:title config) " "))

    ;; Random video button
    (dom/button {:className "btn btn-dark mx-1"
                 :title     "Random video"
                 :onClick   random-video!
                 :style     {:border "0px"}}
      "\u21C5")  ;; shuffle icon substitute

    ;; Search button
    (dom/a {:className "btn btn-dark mx-1"
            :href      "/search"
            :title     "Search"
            :style     {:border "0px"}
            :onClick   (fn [e] (.preventDefault e)
                         (swap! sidebar-state assoc :visible? false)
                         (navigate! "/search"))}
      "\uD83D\uDD0D")  ;; magnifying glass

    ;; Categories toggle
    (dom/button {:className "btn btn-dark mx-1"
                 :title     "Categories"
                 :style     {:border "0px"}
                 :onClick   (fn [_]
                              (swap! sidebar-state update :visible? not))}
      (dom/span {:className "navbar-toggler-icon"}))))

;; --- Sidebar ---
(defn- ui-sidebar []
  (let [{:keys [visible? categories ordering]} @sidebar-state
        sorted-cats (sort-categories categories ordering)]
    (when visible?
      (dom/div {:className "bg-white border-right p-3"
                :style     {:position   "fixed"
                            :top        "56px"
                            :right      "0"
                            :width      "300px"
                            :height     "calc(100vh - 56px)"
                            :overflowY  "auto"
                            :zIndex     "1040"
                            :boxShadow  "-2px 0 5px rgba(0,0,0,0.1)"}}
        (dom/h5 nil "Categories")
        ;; Ordering selector
        (dom/div {:className "mb-2"}
          (dom/small nil "Order by:")
          (dom/select {:className "form-control form-control-sm"
                       :value     ordering
                       :onChange  (fn [e]
                                   (swap! sidebar-state assoc
                                          :ordering (.. e -target -value)))}
            (dom/option {:value "last_updated"} "Last updated")
            (dom/option {:value "use_count"} "Video count")
            (dom/option {:value "name"} "Alphabetical")))
        ;; Category list
        (dom/ul {:className "flex-column list-unstyled"}
          (map (fn [cat]
                 (dom/li {:key       (:slug cat)
                          :className "mr-2 nav-item"}
                   (dom/a {:href    (str "/category/" (:slug cat))
                           :onClick (fn [e]
                                      (.preventDefault e)
                                      (swap! sidebar-state assoc :visible? false)
                                      (navigate! (str "/category/" (:slug cat))))}
                     (:name cat) " ")
                   (dom/small nil
                     (str "(" (:use_count cat) " videos)"))))
               sorted-cats))))))

;; --- Footer ---
(defn- ui-footer [config]
  (dom/footer {:className "text-muted text-center"}
    (dom/div {:className "my-3"}
      (dom/p nil
        "For more resources visit: "
        (dom/a {:href (:website config)} (:website config))))))

;; --- Current page renderer ---
(defn- ui-current-page []
  (let [{:keys [page params]} @current-route]
    (case page
      :home     (home/ui-home-page)
      :video    (do
                  (load-video-page! (:slug params))
                  (video/ui-video-page (:video @page-data)
                                       (:video-playlists @page-data)))
      :category (do
                  (load-category-page! (:slug params))
                  (category/ui-category-page (:category @page-data)))
      :tag      (tag/ui-tag-page (:slug params))
      :search   (search/ui-search-page)
      (home/ui-home-page))))

;; --- Root component ---
(defsc Root [this props]
  {:query         []
   :initial-state {}}
  (let [config (get-app-config)]
    ;; Load categories on mount
    (load-categories!)

    ;; Set up browser history listener
    (set! (.-onpopstate js/window)
          (fn [_] (reset! current-route
                          (parse-route (.-pathname js/location)))))

    ;; Initialize route from current URL
    (when (= :home (:page @current-route))
      (reset! current-route (parse-route (.-pathname js/location))))

    (dom/div nil
      (ui-navbar config)

      ;; Subtitle
      (dom/div {:className "p-1 px-2 mt-2 text-center"}
        (dom/strong nil (:subtitle config)))

      ;; Main content
      (dom/div {:className "container"}
        (dom/div {:className "row"}
          ;; Sidebar
          (ui-sidebar)
          ;; Page content
          (dom/main {:className "col-md-12 col-lg-12 ml-sm-auto px-md-4 pt-4"
                     :role      "main"}
            (ui-current-page))))

      ;; Footer
      (ui-footer config))))

(def ui-root (comp/factory Root))
