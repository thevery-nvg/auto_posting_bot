import enum

from sqlalchemy import (
    Integer,
    BigInteger,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    MetaData,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY
from src.config import settings


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True
    metadata = MetaData(naming_convention=settings.db.naming_convention)


class UserRole(enum.Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"


class PostStatus(enum.Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.USER
    )
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    logs = relationship("Log", back_populates="user")
    posts = relationship("Post", back_populates="creator")


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    moderation_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    comment_chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    notification_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    posts = relationship("Post", back_populates="channel")
    stats = relationship("Stat", back_populates="channel")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("channels.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    photos: Mapped[list[str]] = mapped_column(ARRAY(String), default=None)
    videos: Mapped[list[str]] = mapped_column(ARRAY(String), default=None)
    document: Mapped[str] = mapped_column(String(255), nullable=True,default=None)
    publish_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    published: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, name="poststatus"),
        nullable=False,
        default=PostStatus.PENDING,
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="posts")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="posts")
    stats: Mapped[list["Stat"]] = relationship("Stat", back_populates="post")


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("channels.id"), nullable=True
    )
    timestamp: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="logs")
    channel = relationship("Channel")


class Stat(Base):
    __tablename__ = "stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("channels.id"), nullable=False
    )
    post_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("posts.id"), nullable=True
    )
    views: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    channel = relationship("Channel", back_populates="stats")
    post = relationship("Post", back_populates="stats")
