import enum
from datetime import datetime, timedelta


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

channels_dict={c.id:c for c in channels}

class PostStatus(enum.Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    CANCELLED = "cancelled"

from uuid import uuid4

class Post:
    def __init__(self,
                 channel_id:int,
                 text:str,
                 media_type:str|None,
                 media_file_id:str|None,
                 publish_time:datetime,
                 status:PostStatus,
                 created_by:int,
):
        self.id = uuid4().int
        self.channel_id = channel_id
        self.text = text
        self.media_type = media_type
        self.media_file_id = media_file_id
        self.publish_time = publish_time
        self.created_by = created_by
        self.status = status
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


posts_mock = [
    Post(
        channel_id=-1002164486161,
        text="Тестовый пост1",
        media_type=None,
        media_file_id=None,
        publish_time=datetime.now() + timedelta(seconds=600),
        status=PostStatus.PENDING,
        created_by=123456789,
    ),
    Post(
        channel_id=-1002164486161,
        text="Тестовый пост2",
        media_type=None,
        media_file_id=None,
        publish_time=datetime.now() + timedelta(seconds=700),
        status=PostStatus.PENDING,
        created_by=123456789,
    ),
    Post(
        channel_id=-1002164486161,
        text="Тестовый пост2",
        media_type=None,
        media_file_id=None,
        publish_time=datetime.now() + timedelta(seconds=800),
        status=PostStatus.PENDING,
        created_by=123456789,
    ),
    Post(
        channel_id=-1002164486161,
        text="Тестовый пост2",
        media_type=None,
        media_file_id=None,
        publish_time=datetime.now() + timedelta(seconds=900),
        status=PostStatus.PENDING,
        created_by=123456789,
    ),
    Post(
        channel_id=-1002164486161,
        text="Тестовый пост2",
        media_type=None,
        media_file_id=None,
        publish_time=datetime.now() + timedelta(seconds=1000),
        status=PostStatus.PENDING,
        created_by=123456789,
    ),
    Post(
        channel_id=-1002164486161,
        text="Тестовый пост2",
        media_type=None,
        media_file_id=None,
        publish_time=datetime.now() + timedelta(seconds=1100),
        status=PostStatus.PENDING,
        created_by=123456789,
    ),
    Post(
        channel_id=-1002164486161,
        text="Тестовый пост2",
        media_type=None,
        media_file_id=None,
        publish_time=datetime.now() + timedelta(seconds=1200),
        status=PostStatus.PENDING,
        created_by=123456789,
    ),
    Post(
        channel_id=-1002164486161,
        text="Тестовый пост2",
        media_type=None,
        media_file_id=None,
        publish_time=datetime.now() + timedelta(seconds=1300),
        status=PostStatus.PENDING,
        created_by=123456789,
    ),
    Post(
        channel_id=-1002164486161,
        text="Тестовый пост2",
        media_type=None,
        media_file_id=None,
        publish_time=datetime.now() + timedelta(seconds=1400),
        status=PostStatus.PENDING,
        created_by=123456789,
    ),
]
posts_mock_dict={post.id:post for post in posts_mock}

