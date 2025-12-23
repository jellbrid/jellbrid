from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jellbrid.config import Config
from jellbrid.storage.bad_hashes import BadHash


class BadHashRepo:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.cfg = Config()
        self.session_maker = session_maker

    async def add(self, hash: BadHash):
        if self.cfg.dev_mode:
            return
        async with self.session_maker() as session:
            session.add(hash)

    async def has(self, hash: str):
        async with self.session_maker() as session:
            query = select(BadHash).where(BadHash.hash == hash)  # type: ignore
            results = await session.execute(query)
        return results.fetchone() is not None
