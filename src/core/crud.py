from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.core.models import Channel, Post, PostStatus, User

# Channel CRUD operations
async def get_all_channels(session: AsyncSession):
    result = await session.execute(select(Channel))
    return result.scalars().all()


async def get_active_channels(session: AsyncSession):
    result = await session.execute(
        select(Channel).where(Channel.is_active is True)
    )
    return result.scalars().all()


async def get_inactive_channels(session: AsyncSession):
    result = await session.execute(
        select(Channel).where(Channel.is_active is False)
    )
    return result.scalars().all()


async def get_channel_by_id(session: AsyncSession, channel_id: int):
    result = await session.execute(
        select(Channel)
        .where(Channel.id == channel_id)
        .options(selectinload(Channel.posts), selectinload(Channel.filters))
    )
    return result.scalar_one_or_none()


async def add_channel(session: AsyncSession, channel: Channel):
    session.add(channel)
    await session.commit()
    await session.refresh(channel)
    return channel


async def update_channel(session: AsyncSession, channel: Channel):
    await session.merge(channel)
    await session.commit()
    return channel


async def delete_channel(session: AsyncSession, channel: Channel):
    await session.delete(channel)
    await session.commit()


# Post CRUD operations
async def get_pending_posts(session: AsyncSession):
    result = await session.execute(
        select(Post)
        .where(Post.status == PostStatus.PENDING)
        .options(selectinload(Post.creator), selectinload(Post.channel))
        .order_by(Post.publish_time)
    )
    return result.scalars().all()


async def get_published_posts(session: AsyncSession):
    result = await session.execute(
        select(Post)
        .where(Post.status == PostStatus.PUBLISHED)
        .options(selectinload(Post.creator), selectinload(Post.channel))
        .order_by(Post.publish_time.desc())
    )
    return result.scalars().all()


async def get_cancelled_posts(session: AsyncSession):
    result = await session.execute(
        select(Post)
        .where(Post.status == PostStatus.CANCELLED)
        .options(selectinload(Post.creator), selectinload(Post.channel))
    )
    return result.scalars().all()


async def get_post_by_id(session: AsyncSession, post_id: int):
    result = await session.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(
            selectinload(Post.creator),
            selectinload(Post.channel),
            selectinload(Post.stats)
        )
    )
    return result.scalar_one_or_none()


async def add_post(session: AsyncSession, post: Post):
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post


async def update_post(session: AsyncSession, post: Post):
    await session.merge(post)
    await session.commit()
    return post


async def delete_post(session: AsyncSession, post: Post):
    await session.delete(post)
    await session.commit()