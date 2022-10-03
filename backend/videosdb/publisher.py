from videosdb.db import DB


class Publisher:
    def __init__(self) -> None:
        self.db = DB()
