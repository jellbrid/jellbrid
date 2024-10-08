from sqlalchemy import Column, DateTime, Integer, String, Table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import registry

from jellbrid.config import Config
from jellbrid.storage.active_dls import ActiveDownload

engine = None
mapper_registry = registry()


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def get_session():
    return get_session_maker()()


async def create_db(cfg: Config):
    global engine
    engine = create_async_engine(f"sqlite+aiosqlite:///{cfg.db}")
    async with engine.begin() as conn:
        await conn.run_sync(mapper_registry.metadata.create_all)

    start_mappers()


def start_mappers():
    mapper_registry.map_imperatively(ActiveDownload, active_downloads)


active_downloads = Table(
    "active_downloads",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("imdb_id", String(255), nullable=False),
    Column("tmdb_id", Integer, nullable=False, index=True),
    Column("torrent_id", String(255), nullable=False),
    Column("title", String(526)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("season", Integer, nullable=True),
    Column("episode", Integer, nullable=True),
)
