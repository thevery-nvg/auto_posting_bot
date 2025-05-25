import enum
from datetime import datetime


class Channel:
    def __init__(self, id_:int, name:str, is_active:bool, moderation_enabled:bool, notification_chat_id:int, created_at, updated_at):
        self.id = id_
        self.name = name
        self.is_active = is_active
        self.moderation_enabled = moderation_enabled
        self.notification_chat_id = notification_chat_id
        self.created_at = created_at
        self.updated_at = updated_at

channels = [
        Channel(
            id_=119933,
            name="test1",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119934,
            name="test2",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119935,
            name="test3",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119936,
            name="test4",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119937,
            name="test5",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119938,
            name="test6",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119939,
            name="test7",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119940,
            name="test8",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119941,
            name="test9",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119942,
            name="test10",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119943,
            name="test11",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119944,
            name="test12",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119945,
            name="test13",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119946,
            name="test14",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119947,
            name="test15",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119948,
            name="test16",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119949,
            name="test17",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119950,
            name="test18",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]

class PostStatus(enum.Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    CANCELLED = "cancelled"

class Post:
    def __init__(self,
                 channel_id:int,
                 text:str,
                 media_type:str,
                 media_file_id:str,
                 publish_time:datetime,
                 status:PostStatus,
                 created_by:int,
):

        self.channel_id = channel_id
        self.text = text
        self.media_type = media_type
        self.media_file_id = media_file_id
        self.publish_time = publish_time
        self.created_by = created_by
        self.status = status

# Функция для публикации поста
async def publish_post(bot: Bot, post_id: int, db_session: AsyncSession):
        post = await db_session.get(Post, post_id)
        if not post or post.status != PostStatus.PENDING:
            return

        try:
            if post.media_file_id and post.media_type:
                if post.media_type == "photo":
                    await bot.send_photo(
                        chat_id=post.channel_id,
                        photo=post.media_file_id,
                        caption=post.text,
                        parse_mode="Markdown",
                    )
                elif post.media_type == "video":
                    await bot.send_video(
                        chat_id=post.channel_id,
                        video=post.media_file_id,
                        caption=post.text,
                        parse_mode="Markdown",
                    )
                elif post.media_type == "document":
                    await bot.send_document(
                        chat_id=post.channel_id,
                        document=post.media_file_id,
                        caption=post.text,
                        parse_mode="Markdown",
                    )
            else:
                await bot.send_message(
                    chat_id=post.channel_id, text=post.text, parse_mode="Markdown"
                )

            # Обновляем статус поста
            post.status = PostStatus.PUBLISHED
            await db_session.commit()
        except Exception as e:
            # Логируем ошибку (можно добавить в таблицу logs)
            print(f"Error publishing post {post_id}: {e}")
            post.status = PostStatus.CANCELLED
            await db_session.commit()
