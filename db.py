import os
import shutil
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

# 创建SQLite数据库引擎
SQLALCHEMY_DATABASE_URL = "sqlite:///./sqlite.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# 创建SessionLocal类 - 用于数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建Base类 - 用于模型类继承
Base = declarative_base()

# 用户-群组关联表（多对多关系）
user_group = Table(
    "user_group",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
    Column("joined_at", DateTime, default=lambda: datetime.datetime.now())
)


# 定义User模型
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now())
    is_active = Column(Boolean, default=True)
    # 新增用户档案字段
    avatar_url = Column(String, nullable=True)
    status = Column(String(100), nullable=True)  # 用户状态，如"在线"，"忙碌"等
    bio = Column(Text, nullable=True)  # 用户简介

    # 关系
    messages = relationship("Message", back_populates="sender")
    groups = relationship("Group", secondary=user_group, back_populates="members")


# 定义Group模型
class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now())

    # 关系
    members = relationship("User", secondary=user_group, back_populates="groups")
    messages = relationship("Message", back_populates="group")


# 定义Message模型
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now())
    sender_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))
    
    # 消息类型（text, image, file）
    message_type = Column(String(20), default="text")
    file_url = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)

    # 关系
    sender = relationship("User", back_populates="messages")
    group = relationship("Group", back_populates="messages")


# 获取数据库会话依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 初始化数据库
def init_db():
    # 创建所需目录
    os.makedirs("uploads/avatars", exist_ok=True)
    os.makedirs("uploads/files", exist_ok=True)
    os.makedirs("uploads/images", exist_ok=True)

    # 检查是否存在默认头像，如果不存在，则复制一个
    default_avatar_path = "uploads/avatars/default-avatar.png"
    if not os.path.exists(default_avatar_path):
        # 可以从 src/assets 目录复制默认头像
        src_avatar = os.path.join(os.path.dirname(__file__), "src", "assets", "default-avatar.png")
        if os.path.exists(src_avatar):
            shutil.copy(src_avatar, default_avatar_path)

    # 创建数据库表
    Base.metadata.create_all(bind=engine)