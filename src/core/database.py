from src.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker


async def init_db():
    engine = create_async_engine(
        settings.db.url,
        echo=settings.db.echo,
        echo_pool=settings.db.echo_pool,
        max_overflow=settings.db.max_overflow,
        pool_size=settings.db.pool_size,
    )
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    return engine


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
