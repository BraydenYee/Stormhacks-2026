import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from api.config import settings


class Base(DeclarativeBase):
    pass


def _asyncpg_url(url: str) -> tuple[str, dict]:
    """Convert a libpq-style URL (as Neon/Supabase hand out) into one asyncpg accepts.

    asyncpg rejects `sslmode`/`channel_binding` query params, so strip them and pass
    an SSL context through connect_args instead.
    """
    parts = urlsplit(url)
    scheme = "postgresql+asyncpg"
    query = dict(parse_qsl(parts.query))
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    connect_args: dict = {}
    host = parts.hostname or ""
    local = host in ("localhost", "127.0.0.1", "")
    if sslmode in ("verify-full", "verify-ca"):
        connect_args["ssl"] = ssl.create_default_context()
    elif sslmode != "disable" and (sslmode is not None or not local):
        # Same as libpq's default/`require`: encrypt, but don't verify the certificate chain.
        # Supabase's pooler uses a private CA that Python doesn't trust, so verifying would fail.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx
    # Supabase's pooler (pgbouncer, transaction mode) can't use prepared statement caching.
    if "pooler.supabase.com" in host:
        connect_args["statement_cache_size"] = 0
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), "")), connect_args


def _make_engine():
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set — see .env.example")
    url, connect_args = _asyncpg_url(settings.database_url)
    return create_async_engine(url, connect_args=connect_args, pool_pre_ping=True)


engine = _make_engine() if settings.database_url else None
SessionLocal = async_sessionmaker(engine, expire_on_commit=False) if engine else None


async def get_db():
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not set — see .env.example")
    async with SessionLocal() as db:
        yield db


async def init_db() -> None:
    """Create the pgvector extension, tables and vector indexes (idempotent)."""
    from api import models  # noqa: F401  (register tables)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # Databases created before topics were removed still have `sessions.topic NOT NULL`, which would
        # reject new sessions. Relax it (non-destructive: the old column and the unused `topics` table stay).
        await conn.execute(
            text(
                "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'sessions' AND column_name = 'topic') "
                "THEN ALTER TABLE sessions ALTER COLUMN topic DROP NOT NULL; END IF; END $$"
            )
        )
        for table in ("turns", "mistakes"):
            await conn.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS ix_{table}_embedding_hnsw "
                    f"ON {table} USING hnsw (embedding vector_cosine_ops)"
                )
            )


__all__ = ["Base", "AsyncSession", "SessionLocal", "get_db", "init_db", "engine"]
