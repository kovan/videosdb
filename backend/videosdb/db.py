
from enum import Enum
import anyio
from google.cloud import firestore
from google.oauth2 import service_account
import os
import logging
import sys
from google.api_core.retry import Retry
from videosdb.utils import QuotaExceeded, wait_for_port
logger = logging.getLogger(__name__)


class Counter:
    class Type(Enum):
        READS = 1
        WRITES = 2

    def __init__(self, type: Type, limit: int):
        self.type = type
        self.counter = 0
        self.limit = limit
        self.lock = anyio.Lock()

    async def inc(self, quantity=1):
        async with self.lock:
            self.counter += quantity
            if self.counter > self.limit:
                raise QuotaExceeded(
                    "Surpassed %s ops limit of %s" % (self.type, self.limit))

    def __repr__(self):
        return f"Counter {self.type}: {self.counter}/{self.limit}"


class DB:

    @staticmethod
    def wait_for_port(timeout=30.0):
        if "FIRESTORE_EMULATOR_HOST" in os.environ:
            host, port = os.environ["FIRESTORE_EMULATOR_HOST"].split(":")
            wait_for_port(port, host, timeout)

    @staticmethod
    def get_client(project=None, config=None):
        if not project:
            project = os.environ["FIREBASE_PROJECT"]
        if not config:
            config = os.environ["VIDEOSDB_CONFIG"]

        BASE_DIR = os.path.dirname(sys.modules[__name__].__file__)
        creds_json_path = os.path.join(
            BASE_DIR, "../common/keys/%s.json" % config.strip('"'))

        logger.info("Current project: " + project)
        logger.info("Current config: " + config)
        if "FIRESTORE_EMULATOR_HOST" in os.environ:
            logger.info("USING EMULATOR: %s",
                        os.environ["FIRESTORE_EMULATOR_HOST"])
        else:
            logger.info("USING LIVE DATABASE")
        db = firestore.AsyncClient(project=project,
                                   credentials=service_account.Credentials.from_service_account_file(
                                       creds_json_path))

        return db

    def __init__(self, prefix=""):
        self.prefix = prefix

        self.FREE_TIER_WRITE_QUOTA = 20000
        self.FREE_TIER_READ_QUOTA = 50000
        # leave 20000 for yarn generate and visitors
        self._read_counter = Counter(Counter.Type.READS,
                                     self.FREE_TIER_READ_QUOTA)
        self._write_counter = Counter(Counter.Type.WRITES,
                                      self.FREE_TIER_WRITE_QUOTA - 500)

        self._db = self.get_client()

    async def init(self):
        # initialize meta table:
        doc = await self._document("meta/video_ids").get()
        if not doc.exists or "videoIds" not in doc.to_dict():
            await doc.reference.set(
                {"videoIds": list()}
            )
        doc = await self._document("meta/state").get()
        if not doc.exists:
            await doc.reference.set({})
        # check writes are not out of quota:
        await self.set("meta/test", {})
        return self

    # google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded.

    def _document(self, path):
        return self._db.document(self.prefix + path)

    def _collection(self, path):
        return self._db.collection(self.prefix + path)
    # ---------------------- PUBLIC -------------------------------

    async def adjust_read_limit(self, new_limit: int):
        async with self._read_counter.lock:
            if self._read_counter.limit < new_limit:
                self._read_counter.limit = self.FREE_TIER_READ_QUOTA - new_limit

    @Retry()
    async def set(self, path, *args, **kwargs):
        await self._write_counter.inc()
        return await self._document(path).set(*args, **kwargs)

    @Retry()
    async def get(self, path, *args, **kwargs):
        await self._read_counter.inc()
        return await self._document(path).get(*args, **kwargs)

    @Retry()
    async def update(self, path, *args, **kwargs):
        await self._write_counter.inc()
        return await self._document(path).update(*args, **kwargs)

    @Retry()
    def stream(self, collection_name):
        return self._collection(collection_name).stream()

    @Retry()
    async def recursive_delete(self, path):
        ref = self._document(path)
        return await self._db.recursive_delete(ref)

    @Retry()
    async def set_noquota(self, path, *args, **kwargs):
        return await self._document(path).set(*args, **kwargs)

    @Retry()
    async def update_noquota(self, path, *args, **kwargs):
        return await self._document(path).update(*args, **kwargs)

    @Retry()
    async def get_noquota(self, path, *args, **kwargs):
        return await self._document(path).get(*args, **kwargs)
