from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jellbrid.config import Config
from jellbrid.storage.bad_hashes import BadHash


class BadHashRepo:
    def __init__(self, session: AsyncSession):
        self.cfg = Config()
        self.session = session

    async def add(self, hash: BadHash):
        if self.cfg.dev_mode:
            return
        async with self.session.begin():
            self.session.add(hash)

    async def has(self, hash: str):
        async with self.session.begin():
            query = select(BadHash).where(BadHash.hash == hash)  # type: ignore
            results = await self.session.execute(query)
        return results.fetchone() is not None
