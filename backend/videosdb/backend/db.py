from google.cloud import firestore


class DB:
    def __init__(self):
        self.db = firestore.AsyncClient()

    async def delete_collection(collection_ref):
        async for doc in collection_ref.stream():
            await doc.reference.delete()
