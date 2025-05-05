from sqlalchemy import (
    Column,
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
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func

import enum

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

    id = Column(BigInteger, primary_key=True, index=True)  # Telegram ID пользователя
    username = Column(String(255), nullable=True)  # Имя пользователя (опционально)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)  # Роль
    is_banned = Column(Boolean, default=False)  # Статус бана
    created_at = Column(DateTime, server_default=func.now())  # Время создания
    updated_at = Column(DateTime, onupdate=func.now())  # Время обновления

    logs = relationship("Log", back_populates="user")


class Channel(Base):
    __tablename__ = "channels"

    id = Column(BigInteger, primary_key=True, index=True)  # Telegram ID канала
    name = Column(String(255), nullable=False)  # Название канала
    is_active = Column(Boolean, default=True)  # Активен ли канал
    moderation_enabled = Column(Boolean, default=True)  # Включена ли модерация
    notification_chat_id = Column(BigInteger, nullable=True)  # Чат для уведомлений
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Связи
    posts = relationship("Post", back_populates="channel")
    filters = relationship("Filter", back_populates="channel")
    stats = relationship("Stat", back_populates="channel")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, ForeignKey("channels.id"), nullable=False)
    text = Column(Text, nullable=True)  # Текст поста
    media_type = Column(String(50), nullable=True)  # Тип медиа (photo, video, document)
    media_file_id = Column(String(255), nullable=True)  # File ID медиа в Telegram
    publish_time = Column(DateTime, nullable=False)  # Время публикации
    status = Column(
        Enum(PostStatus), nullable=False, default=PostStatus.PENDING
    )  # Статус
    created_by = Column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )  # Кто создал
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Связи
    channel = relationship("Channel", back_populates="posts")
    creator = relationship("User")


class Filter(Base):
    __tablename__ = "filters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, ForeignKey("channels.id"), nullable=False)
    keyword = Column(String(255), nullable=True)  # Ключевое слово
    regex = Column(String(255), nullable=True)  # Регулярное выражение
    is_active = Column(Boolean, default=True)  # Активен ли фильтр
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Связь
    channel = relationship("Channel", back_populates="filters")


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    action = Column(String(255), nullable=False)  # Тип действия (ban, delete, post)
    details = Column(Text, nullable=True)  # Подробности (JSON или текст)
    channel_id = Column(BigInteger, ForeignKey("channels.id"), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())

    # Связи
    user = relationship("User", back_populates="logs")
    channel = relationship("Channel")


class Stat(Base):
    __tablename__ = "stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, ForeignKey("channels.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)  # Связь с постом
    views = Column(Integer, default=0)  # Количество просмотров
    comments = Column(Integer, default=0)  # Количество комментариев
    timestamp = Column(DateTime, server_default=func.now())

    # Связь
    channel = relationship("Channel", back_populates="stats")
    post = relationship("Post")
