from src.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    async_sessionmaker,
    AsyncSession,
)
from loguru import logger

async def init_db() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        str(settings.db.url),
        echo=settings.db.echo,
        echo_pool=settings.db.echo_pool,
        max_overflow=settings.db.max_overflow,
        pool_size=settings.db.pool_size,
    )

    # Проверка подключения
    async with engine.connect() as conn:
        msg = await conn.execute(text("SELECT version() as ver;"))
    logger.info(f"Database connection test successful! {msg.scalars().first()}")
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    return engine, session_factory


class DatabaseManager:
    def __init__(
        self,
        url: str,
        echo: bool = False,
        echo_pool: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        self.engine: AsyncEngine = create_async_engine(
            url,
            echo=echo,
            echo_pool=echo_pool,
            max_overflow=max_overflow,
            pool_size=pool_size,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def dispose(self):
        await self.engine.dispose()

    async def get_async_session(self):
        async with self.session_factory() as session:
            yield session

db_manager = DatabaseManager(
    url=str(settings.db.url),
    echo=settings.db.echo,
    echo_pool=settings.db.echo_pool,
    pool_size=settings.db.pool_size,
    max_overflow=settings.db.max_overflow,
)
