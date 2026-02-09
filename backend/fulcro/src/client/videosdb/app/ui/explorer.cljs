(ns videosdb.app.ui.explorer
  "Infinite scroll + sort/filter component. Replaces Explorer.vue."
  (:require [com.fulcrologic.fulcro.dom :as dom]
            [com.fulcrologic.fulcro.components :as comp :refer [defsc]]
            [videosdb.app.firebase :as fb]
            [videosdb.app.ui.loading :as loading]
            [videosdb.util :as util]
            [clojure.string :as str]))

;; --- Ordering options ---
(def ordering-options
  [{:text "Latest"         :field "snippet.publishedAt"      :direction "desc"}
   {:text "Oldest"         :field "snippet.publishedAt"      :direction "asc"}
   {:text "Most viewed"    :field "statistics.viewCount"     :direction "desc"}
   {:text "Most liked"     :field "statistics.likeCount"     :direction "desc"}
   {:text "Most commented" :field "statistics.commentCount"  :direction "desc"}
   {:text "Most favorited" :field "statistics.favoriteCount" :direction "desc"}
   {:text "Longest"        :field "videosdb.durationSeconds" :direction "desc"}
   {:text "Shortest"       :field "videosdb.durationSeconds" :direction "asc"}
   {:text "Alphabetical"   :field "snippet.title"            :direction "asc"}])

(def PAGE_SIZE 20)

;; --- Explorer state atom (component-local) ---
(defonce explorer-state
  (atom {:videos      {}
         :ordering    (first ordering-options)
         :cursor      nil
         :no-more?    false
         :loading?    false
         :category    nil
         :tag         nil}))

(defn- format-duration [seconds]
  (when seconds
    (try
      (let [d (js/Date. (* seconds 1000))]
        (subs (.toISOString d) 11 19))
      (catch :default _ "00:00:00"))))

(defn- do-query!
  "Execute a Firestore query and update state."
  [state-atom]
  (when-not (:no-more? @state-atom)
    (swap! state-atom assoc :loading? true)
    (let [{:keys [ordering cursor category tag]} @state-atom]
      (-> (fb/query-videos-page
           {:order-field (:field ordering)
            :order-dir   (:direction ordering)
            :category-id (when category (:id category))
            :tag         tag
            :cursor      cursor
            :page-size   PAGE_SIZE})
          (.then (fn [{:keys [docs cursor count]}]
                   (let [new-videos (reduce (fn [m d]
                                              (let [id (.-id d)]
                                                (assoc m id d)))
                                            {}
                                            docs)]
                     (swap! state-atom
                            (fn [s]
                              (-> s
                                  (update :videos merge new-videos)
                                  (assoc :cursor cursor)
                                  (assoc :no-more? (< count PAGE_SIZE))
                                  (assoc :loading? false)))))))
          (.catch (fn [err]
                    (js/console.error "Explorer query error:" err)
                    (swap! state-atom assoc :loading? false)))))))

(defn- handle-ordering-change! [state-atom idx]
  (swap! state-atom assoc
         :ordering (nth ordering-options idx)
         :videos   {}
         :cursor   nil
         :no-more? false)
  (do-query! state-atom))

;; --- Intersection Observer for infinite scroll ---
(defn- setup-infinite-scroll! [state-atom sentinel-el]
  (when sentinel-el
    (let [observer (js/IntersectionObserver.
                    (fn [entries]
                      (let [entry (first (array-seq entries))]
                        (when (and (.-isIntersecting entry)
                                   (not (:loading? @state-atom))
                                   (not (:no-more? @state-atom)))
                          (do-query! state-atom))))
                    #js {:rootMargin "100px"})]
      (.observe observer sentinel-el)
      observer)))

;; --- Video card ---
(defn- ui-video-card [video idx]
  (let [data     (if (object? video) (js->clj video :keywordize-keys true) video)
        snippet  (:snippet data)
        videosdb (:videosdb data)
        slug     (:slug videosdb)
        title    (:title snippet)
        thumb    (get-in snippet [:thumbnails :medium :url])
        date     (:publishedAt snippet)
        duration (:durationSeconds videosdb)]
    (dom/div {:className "col-md-4" :key (or (:id data) idx)}
      (dom/div {:className "card mb-4 shadow-sm text-center"}
        (dom/a {:href (str "/video/" slug)}
          (dom/img {:className "bd-placeholder-img card-img-top"
                    :src       thumb
                    :height    "180"
                    :width     "320"
                    :loading   (if (< idx 6) "eager" "lazy")
                    :alt       title}))
        (dom/div {:className "card-body"}
          (dom/p {:className "card-text"}
            (dom/a {:href (str "/video/" slug)} title))
          (dom/div {:className "d-flex justify-content-between align-items-center"}
            (dom/small {:className "text-muted"}
              "Published: " (dom/br nil)
              (util/format-date date))
            (dom/small {:className "text-muted"}
              "Duration (hh:mm:ss): " (dom/br nil)
              (format-duration duration))))))))

;; --- Main Explorer component ---
(defn ui-explorer
  "Explorer component with infinite scroll, ordering, and filtering.
   Props: {:category cat-map, :tag tag-string}"
  [props]
  (let [state-atom (atom (merge @explorer-state
                                {:category (:category props)
                                 :tag      (:tag props)}))]
    ;; Use a local state atom for this instance
    ;; Reset if category/tag changed
    (when (or (not= (:category @explorer-state) (:category props))
              (not= (:tag @explorer-state) (:tag props)))
      (reset! explorer-state
              {:videos   {}
               :ordering (first ordering-options)
               :cursor   nil
               :no-more? false
               :loading? false
               :category (:category props)
               :tag      (:tag props)})
      (do-query! explorer-state))

    ;; Initial load if empty
    (when (empty? (:videos @explorer-state))
      (do-query! explorer-state))

    (let [{:keys [videos ordering loading?]} @explorer-state
          sorted-videos (sort-by (fn [[_ v]]
                                   (let [d (if (object? v) (js->clj v :keywordize-keys true) v)]
                                     (get-in d [(keyword (first (str/split (:field ordering) #"\.")))
                                                (keyword (second (str/split (:field ordering) #"\.")))])))
                                 (if (= "desc" (:direction ordering)) #(compare %2 %1) compare)
                                 videos)]
      (dom/div {:className "pt-2"}
        (dom/div {:className "album py-1 bg-light"}
          (dom/div {:className "px-3"}
            ;; Ordering selector
            (dom/div {:className "row"}
              (dom/div {:className "col"}
                (dom/div {:className "container p-2 text-right"} "Order by:"))
              (dom/div {:className "col"}
                (dom/div {:className "container p-1 pb-3"}
                  (dom/select
                    {:className "form-control"
                     :value     (.indexOf (to-array (map :text ordering-options))
                                          (:text ordering))
                     :onChange  (fn [e]
                                 (handle-ordering-change!
                                  explorer-state
                                  (js/parseInt (.. e -target -value))))}
                    (map-indexed
                     (fn [idx opt]
                       (dom/option {:key idx :value idx} (:text opt)))
                     ordering-options)))))

            ;; Video grid
            (when (seq sorted-videos)
              (dom/div {:className "row"}
                (map-indexed
                 (fn [idx [_ video]]
                   (ui-video-card video idx))
                 sorted-videos)
                ;; Loading indicator
                (when loading?
                  (dom/div {:className "col-md-4"}
                    (dom/div {:className "card mb-4 shadow-sm text-center"}
                      "Loading")))))

            ;; Sentinel element for infinite scroll
            (dom/div {:ref (fn [el] (setup-infinite-scroll! explorer-state el))
                      :style {:height "1px"}})))))))
