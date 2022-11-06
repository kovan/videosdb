(import json)
(import anyio)
(import os)
(import sys)
(import logging)
(import google.api_core.retry [Retry])
(import google.cloud [firestore] )
(import videosdb.utils [QuotaExceeded])


(defn get-client [
    [project None]
    [config None]]
    (print os.environ.get("SDF"))


)
