
from google.cloud import firestore
from google.oauth2 import service_account
import os
import logging
import sys

logger = logging.getLogger(__name__)


class DB:
    class QuotaExceeded(Exception):
        pass

    @staticmethod
    def setup(project, config):
        BASE_DIR = os.path.dirname(sys.modules[__name__].__file__)
        creds_json_path = os.path.join(
            BASE_DIR, "keys/%s.json" % config.strip('"'))

        logger.info("Current project: " + project)
        db = firestore.AsyncClient(project=project,
                                   credentials=service_account.Credentials.from_service_account_file(
                                       creds_json_path))

        return db

    def __init__(self):
        project = os.environ["FIREBASE_PROJECT"]
        config = os.environ["VIDEOSDB_CONFIG"]
        self.write_count = 0
        self.WRITE_LIMIT = 19500
        self.read_count = 0
        self.READ_LIMIT = 42000
        self._db = self.setup(project, config)

    def _meta_ref(self):
        return self._db.collection("meta").document("meta")

    async def init(self):
        # initialize meta table:
        doc = await self._meta_ref().get()
        if not doc.exists or "videoIds" not in doc.to_dict():
            await self._meta_ref().set(
                {"videoIds": list()}
            )
        return self

    async def get_video_count(self):
        doc = await self._meta_ref().get()
        if doc.exists:
            return len(doc.get("videoIds"))
        else:
            return 0

    # google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded.

    def _read_inc(self):
        self.read_count += 1
        if self.read_count > self.READ_LIMIT:
            raise self.QuotaExceeded()

    def _write_inc(self):
        self.write_count += 1
        if self.write_count > self.WRITE_LIMIT:
            raise self.QuotaExceeded()

    async def set(self, path, *args, **kwargs):
        self._write_inc()
        return await self._db.document(path).set(*args, **kwargs)

    async def get(self, path, *args, **kwargs):
        self._read_inc()
        return await self._db.document(path).get(*args, **kwargs)

    async def update(self, path, *args, **kwargs):
        self._write_inc()
        return await self._db.document(path).update(*args, **kwargs)

    def stream(self, collection_name):
        return self.Streamer(self, collection_name)

    async def recursive_delete(self, path):
        ref = self._db.document(path)
        return await self._db.recursive_delete(ref)

    class Streamer:
        def __init__(self, db, collection_name):
            self.db = db
            self.collection_name = collection_name

        def __aiter__(self):
            self.generator = self.db._db.collection(
                self.collection_name).stream()
            return self.generator

        async def __anext__(self):
            self.db._read_inc()
            yield anext(self.generator)
