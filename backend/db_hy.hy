(import json)
(import anyio)
(import os)
(import sys)
(import logging)
(import google.api_core.retry [Retry])
(import google.cloud [firestore] )
(import videosdb.utils [QuotaExceeded  get_module_path])
(import google.oauth2.service_account [Credentials])

(setv BASE_DIR (get_module_path))
(setv COMMON_DIR (+ BASE_DIR "/../common"))
; (if not COMMON_DIR)


; if not os.path.exists(COMMON_DIR):
;     COMMON_DIR = BASE_DIR + "/../common"

; (os.environ.get "VIDEOSDB_CONFIG" "testing")
(defn get-client [
    [project None]

    [config  None]]

    (firestore.AsyncClient
        project
        (Credentials.from_service_account_file
            (os.path.join
                COMMON_DIR
                (os.path.join
                    COMMON_DIR (% "keys/%s.json" config)))))
)
