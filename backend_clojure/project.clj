(defproject videosdb "1.0.0"
  :description "VideosDB - YouTube channel synchronization and management system"
  :url "https://github.com/yourusername/videosdb"
  :license {:name "EPL-2.0 OR GPL-2.0-or-later WITH Classpath-exception-2.0"
            :url "https://www.eclipse.org/legal/epl-2.0/"}

  :dependencies [[org.clojure/clojure "1.11.1"]

                 ;; Logging
                 [org.clojure/tools.logging "1.2.4"]
                 [com.taoensso/timbre "6.2.2"]

                 ;; JSON processing
                 [org.clojure/data.json "2.4.0"]
                 [cheshire "5.11.0"]

                 ;; HTTP client
                 [clj-http "3.12.3"]

                 ;; Firebase/Firestore
                 [com.google.cloud/google-cloud-firestore "3.32.1"]

                 ;; Redis client
                 [com.taoensso/carmine "3.5.0-alpha11"]

                 ;; Async
                 [org.clojure/core.async "1.6.673"]
                 [manifold "0.3.0"]

                 ;; Environment configuration
                 [environ "1.2.0"]

                 ;; Utilities
                 [clj-time "0.15.2"]
                 [slugger "1.0.1"]
                 [slingshot "0.12.2"]

                 ;; Code analysis (for development)
                 [org.clojure/tools.analyzer "1.1.0"]
                 [org.clojure/tools.analyzer.jvm "1.2.2"]]

  :main ^:skip-aot videosdb.core

  :target-path "target/%s"

  :source-paths ["src"]
  :test-paths ["test"]
  :resource-paths ["resources"]

  :profiles {:dev {:dependencies [[nrepl "1.0.0"]
                                  [midje "1.10.9"]]
                   :plugins [[lein-midje "3.2.1"]]}

             :uberjar {:aot :all
                       :jvm-opts ["-Dclojure.compiler.direct-linking=true"]}}

  :repl-options {:init-ns videosdb.main
                 :timeout 120000}

  :jvm-opts ["-Xmx2g" "-server"]

  :aliases {"sync" ["run" "-m" "videosdb.main" "sync"]
            "ipfs" ["run" "-m" "videosdb.main" "ipfs"]
            "publish" ["run" "-m" "videosdb.main" "publish"]
            "stats" ["run" "-m" "videosdb.main" "stats"]
            "setup" ["run" "-m" "videosdb.main" "setup"]
            "test-all" ["midje"]}

  :clean-targets ^{:protect false} ["target"])