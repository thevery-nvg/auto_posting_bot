import tenacity
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text, create_engine

from tenacity import _utils
from src.config import settings
from loguru import logger as logger

def before_log(retry_state: tenacity.RetryCallState) -> None:
    if retry_state.outcome is None:
        return
    if retry_state.outcome.failed:
        verb, value = "raised", retry_state.outcome.exception()
    else:
        verb, value = "returned", retry_state.outcome.result()
    # logger = retry_state.kwargs["logger"]
    logger.info(
        "Retrying {callback} in {sleep} seconds as it {verb} {value}".format(
            callback=_utils.get_callback_name(retry_state.fn),  # type: ignore[arg-type]
            sleep=retry_state.next_action.sleep,  # type: ignore[union-attr]
            verb=verb,
            value=value,
        ),
        callback=_utils.get_callback_name(retry_state.fn),  # type: ignore[arg-type]
        sleep=retry_state.next_action.sleep,  # type: ignore[union-attr]
        verb=verb,
        value=value,
    )


def after_log(retry_state: tenacity.RetryCallState) -> None:
    # logger = retry_state.kwargs["logger"]
    logger.info(
        "Finished call to {callback!r} after {time:.2f}, this was the {attempt} time calling it.".format(
            # type: ignore[str-format]
            callback=_utils.get_callback_name(retry_state.fn),  # type: ignore[arg-type]
            time=retry_state.seconds_since_start,
            attempt=_utils.to_ordinal(retry_state.attempt_number),
        ),
        callback=_utils.get_callback_name(retry_state.fn),  # type: ignore[arg-type]
        time=retry_state.seconds_since_start,
        attempt=_utils.to_ordinal(retry_state.attempt_number),
    )



@tenacity.retry(
    wait=tenacity.wait_fixed(2),
    stop=tenacity.stop_after_delay(5),
    before_sleep=before_log,
    after=after_log,
)
async def wait_sqlalchemy() -> AsyncSession:
    engine = create_async_engine(
        str(settings.db.url),
        echo=settings.db.echo,
        echo_pool=settings.db.echo_pool,
        max_overflow=settings.db.max_overflow,
        pool_size=settings.db.pool_size,)
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with async_session() as s:
        version = await s.execute(text("SELECT version() as ver;"))
    logger.debug("Connected to SQLAlchemy database.", version=version.first())
    return async_session()