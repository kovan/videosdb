from videosdb.utils import get_module_path
import json
from enum import Enum
import anyio
from google.cloud import firestore
from google.oauth2 import service_account
import os
import logging
import sys
from google.api_core.retry import Retry
from jsonschema import validate
from videosdb.utils import QuotaExceeded, wait_for_port
logger = logging.getLogger(__name__)


class CounterTypes(Enum):
    READS = 1
    WRITES = 2


class Counter:

    def __init__(self, type: CounterTypes, limit: int):
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
            wait_for_port(int(port), host, timeout)

    @staticmethod
    def get_client(project=None, config=None):
        if not config:
            config = os.environ.get("VIDEOSDB_CONFIG", "testing")
        if not project:
            project = os.environ.get("FIREBASE_PROJECT", "videosdb-testing")

        BASE_DIR = os.path.dirname(str(sys.modules[__name__].__file__))
        creds_json_path = os.path.join(
            BASE_DIR, "../common/keys/%s.json" % config.strip('"'))

        if "FIRESTORE_EMULATOR_HOST" in os.environ:
            project = "demo-project"
            logger.info("USING EMULATOR: %s",
                        os.environ["FIRESTORE_EMULATOR_HOST"])
        else:
            logger.info("USING LIVE DATABASE")
        logger.info("Current project: " + project)
        logger.info("Current config: " + config)

        db = firestore.AsyncClient(project=project,
                                   credentials=service_account.Credentials.from_service_account_file(
                                       creds_json_path))

        return db

    def __init__(self,):

        self.FREE_TIER_WRITE_QUOTA = 20000
        self.FREE_TIER_READ_QUOTA = 50000

        self._counters = {
            CounterTypes.READS:
                Counter(CounterTypes.READS,
                        self.FREE_TIER_READ_QUOTA - 5000),
            CounterTypes.WRITES:
                Counter(CounterTypes.WRITES,
                        self.FREE_TIER_WRITE_QUOTA - 500)
        }

        self._db = self.get_client()

    async def init(self):
        # initialize meta table:
        doc = await self._db.document("meta/video_ids").get()
        if not doc.exists or "videoIds" not in doc.to_dict():  # type: ignore
            await doc.reference.set(  # type: ignore
                {"videoIds": list()}
            )
        doc = await self._db.document("meta/state").get()
        if not doc.exists:  # type: ignore
            await doc.reference.set({})  # type: ignore
        # check writes are not out of quota:
        await self.set("meta/test", {})
        return self

    # ---------------------- PUBLIC -------------------------------

    def get_stats(self):
        read_c = self._counters[CounterTypes.READS]
        write_c = self._counters[CounterTypes.WRITES]
        return {
            str(read_c),
            str(write_c),
        }

    async def increase_counter(self, type: CounterTypes, increase: int = 1):
        await self._counters[type].inc(increase)

    @Retry()
    async def set(self, path, *args, **kwargs):
        await self._counters[CounterTypes.WRITES].inc()
        return await self._db.document(path).set(*args, **kwargs)

    @Retry()
    async def get(self, path, *args, **kwargs):
        await self._counters[CounterTypes.READS].inc()
        return await self._db.document(path).get(*args, **kwargs)

    @Retry()
    async def update(self, path, *args, **kwargs):
        await self._counters[CounterTypes.WRITES].inc()
        return await self._db.document(path).update(*args, **kwargs)

    @Retry()
    async def delete(self, path, *args, **kwargs):
        await self._counters[CounterTypes.WRITES].inc()
        return await self._db.document(path).delete(*args, **kwargs)

    @Retry()
    async def recursive_delete(self, path):
        ref = self._db.document(path)
        return await self._db.recursive_delete(ref)

    @Retry()
    async def set_noquota(self, path, *args, **kwargs):
        return await self._db.document(path).set(*args, **kwargs)

    @Retry()
    async def update_noquota(self, path, *args, **kwargs):
        return await self._db.document(path).update(*args, **kwargs)

    @Retry()
    async def get_noquota(self, path, *args, **kwargs):
        return await self._db.document(path).get(*args, **kwargs)

    async def validate_videos_schema(self):
        with open(get_module_path() + "/../../common/firebase/db-schema.json") as f:
            schema = json.load(f)

        async for doc_ref in self._db.collection("videos").list_documents():
            video = await doc_ref.get()  # type: ignore
            await self._counters[CounterTypes.READS].inc()
            video_dict = video.to_dict()
            validate(instance=video_dict, schema=schema)
