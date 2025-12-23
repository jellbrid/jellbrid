from pathlib import Path

import anyio
import anyio.to_thread
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import registry

from jellbrid.config import Config
from jellbrid.storage.active_dls import ActiveDownload
from jellbrid.storage.bad_hashes import BadHash

meta = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


engine = None
mapper_registry = registry(metadata=meta)


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_db(cfg: Config):
    global engine
    engine = create_async_engine(f"sqlite+aiosqlite:///{cfg.db}")
    async with engine.begin() as conn:
        await conn.run_sync(mapper_registry.metadata.create_all)
        await conn.exec_driver_sql("PRAGMA journal_mode = WAL")
        await conn.exec_driver_sql("PRAGMA busy_timeout = 5000")
        await run_migrations()

    start_mappers()


async def run_migrations():
    config_file = Path(__file__).parent / Path("alembic/alembic.ini")
    acfg = AlembicConfig(config_file)
    await anyio.to_thread.run_sync(command.upgrade, acfg, "head")


def start_mappers():
    mapper_registry.map_imperatively(ActiveDownload, active_downloads)
    mapper_registry.map_imperatively(BadHash, bad_hashes)


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

bad_hashes = Table(
    "bad_hashes",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("hash", String(255), nullable=False, index=True),
    Column("filename", String(255), nullable=False),
    Column("status", String(526)),
    Column("progress", Float),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
