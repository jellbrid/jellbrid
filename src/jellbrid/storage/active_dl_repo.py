from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jellbrid.config import Config
from jellbrid.storage.active_dls import ActiveDownload


class ActiveDownloadRepo:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.cfg = Config()
        self.session_maker = session_maker

    async def add(self, download: ActiveDownload):
        if self.cfg.dev_mode:
            return
        async with self.session_maker() as session:
            session.add(download)
            await session.commit()

    async def delete(self, download: ActiveDownload):
        async with self.session_maker() as session:
            await session.delete(download)
            await session.commit()

    async def has_movie(self, imdb_id: str):
        async with self.session_maker() as session:
            query = select(ActiveDownload).where(ActiveDownload.imdb_id == imdb_id)  # type: ignore
            results = await session.execute(query)
        return results.fetchone() is not None

    async def has_season(self, imdb_id: str, season: int):
        async with self.session_maker() as session:
            query = (
                select(ActiveDownload)
                .where(ActiveDownload.imdb_id == imdb_id)  # type: ignore
                .where(ActiveDownload.season == season)  # type: ignore
            )
            results = await session.execute(query)
        return results.fetchone() is not None

    async def has_episode(self, imdb_id: str, season: int, episode: int):
        async with self.session_maker() as session:
            query = (
                select(ActiveDownload)
                .where(ActiveDownload.imdb_id == imdb_id)  # type: ignore
                .where(ActiveDownload.season == season)  # type: ignore
                .where(ActiveDownload.episode == episode)  # type: ignore
            )
            results = await session.execute(query)
        return results.fetchone() is not None

    async def get_requests(self):
        async with self.session_maker() as session:
            query = select(ActiveDownload)
            results = await session.scalars(query)
        return results.all()

    async def get_by_did(self, did: str) -> ActiveDownload | None:
        async with self.session_maker() as session:
            query = (
                select(ActiveDownload).where(ActiveDownload.torrent_id == did)  # type: ignore
            )
            return await session.scalar(query)

    async def delete_by_did(self, did: str) -> None:
        async with self.session_maker() as session:
            query = delete(ActiveDownload).where(ActiveDownload.torrent_id == did)  # type: ignore
            await session.execute(query)
            await session.commit()
