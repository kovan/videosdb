(ns videosdb.app.ui.video
  "Video detail page. Replaces Video.vue."
  (:require [com.fulcrologic.fulcro.dom :as dom]
            [com.fulcrologic.fulcro.components :as comp :refer [defsc]]
            [videosdb.app.firebase :as fb]
            [videosdb.util :as util]
            [clojure.string :as str]))

(defn- video-structured-data
  "Generate JSON-LD structured data for a video."
  [video]
  (let [snippet  (.-snippet video)
        videosdb (.-videosdb video)
        content  (.-contentDetails video)]
    (js/JSON.stringify
     #js {"@context"     "https://schema.org"
          "@type"        "VideoObject"
          "name"         (.-title snippet)
          "description"  (or (.-description snippet) (.-title snippet))
          "thumbnailUrl" (let [thumbs (.-thumbnails snippet)]
                           (clj->js (map #(.-url %)
                                         (js/Object.values thumbs))))
          "uploadDate"   (util/date-to-iso (.-publishedAt snippet))
          "duration"     (when content (.-duration content))
          "embedUrl"     (str "https://www.youtube.com/watch?v=" (.-id video))})))

(defn- format-duration [seconds]
  (when seconds
    (try
      (subs (.toISOString (js/Date. (* seconds 1000))) 11 19)
      (catch :default _ "00:00:00"))))

(defn- ui-category-card [item]
  (let [snippet  (.-snippet item)
        videosdb (.-videosdb item)]
    (dom/div {:className "col-md-4" :key (.-id item)}
      (dom/div {:className "card mb-4 shadow-sm text-center"}
        (dom/a {:href (str "/category/" (.-slug videosdb))}
          (dom/img {:className "bd-placeholder-img card-img-top"
                    :src       (.. snippet -thumbnails -medium -url)
                    :height    "180"
                    :width     "320"
                    :alt       (.-title snippet)}))
        (dom/div {:className "card-body"}
          (dom/p {:className "card-text"}
            (dom/a {:href (str "/category/" (.-slug videosdb))}
              (.-title snippet))))))))

(defn- ui-tag-badge [tag]
  (dom/a {:className "p-1"
          :href      (str "/tag/" (js/encodeURIComponent tag))
          :key       tag}
    (dom/span {:className "badge badge-light"} tag)))

(defn ui-video-page
  "Video detail page component. Expects a video JS object."
  [video playlists]
  (when video
    (let [snippet  (.-snippet video)
          videosdb (.-videosdb video)
          tags     (.-tags snippet)]
      (dom/div {:className "container m-0 p-0 mx-auto"}
        ;; JSON-LD
        (dom/script {:type                    "application/ld+json"
                     :dangerouslySetInnerHTML {:__html (video-structured-data video)}})

        (dom/div {:className "card m-0 p-0"}
          ;; Title and meta
          (dom/div {:className "my-4"}
            (dom/h1 nil (.-title snippet))
            (dom/p nil
              (dom/small nil
                "Published: " (util/format-date (.-publishedAt snippet)) ". "
                "Duration: " (format-duration (.-durationSeconds videosdb))))

            ;; YouTube embed
            (dom/p {:align "center"}
              (dom/iframe {:src             (str "https://www.youtube.com/embed/" (.-id video)
                                                 "?autoplay=1")
                           :width           "100%"
                           :height          "500"
                           :frameBorder     "0"
                           :allow           "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                           :allowFullScreen true
                           :loading         "lazy"})))

          ;; Description
          (when (.-descriptionTrimmed videosdb)
            (dom/div {:className "my-4"}
              (dom/strong nil "Description")
              (dom/p {:style                   {:whiteSpace "pre-line"}
                      :dangerouslySetInnerHTML {:__html (.-descriptionTrimmed videosdb)}})))

          ;; Categories
          (when (and playlists (pos? (count playlists)))
            (dom/div {:className "my-4"}
              (dom/p nil (dom/h2 nil "In categories:"))
              (dom/div {:className "album py-1"}
                (dom/div {:className "row"}
                  (map ui-category-card playlists)))))

          ;; Tags
          (when (and tags (pos? (.-length tags)))
            (dom/div {:className "my-4"}
              (dom/p {:className "text-center"}
                (dom/strong nil "Tags:"))
              (dom/p {:className "text-center"}
                (map ui-tag-badge (array-seq tags))))))))))
