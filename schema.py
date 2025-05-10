from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, HttpUrl


# 用户相关模型
class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserLogin(UserBase):
    password: str


class UserProfile(BaseModel):
    avatar_url: Optional[str] = None
    status: Optional[str] = None
    bio: Optional[str] = None


class UserProfileUpdate(UserProfile):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime
    is_active: bool
    avatar_url: Optional[str] = None
    status: Optional[str] = None
    bio: Optional[str] = None

    class Config:
        from_attributes = True


# 群组相关模型
class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None


class GroupCreate(GroupBase):
    pass


class GroupResponse(GroupBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class GroupDetailResponse(GroupResponse):
    members: List[UserResponse]

    class Config:
        from_attributes = True


# 消息相关模型
class MessageBase(BaseModel):
    content: str
    message_type: str = "text"  # text, image, file
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None


class MessageCreate(MessageBase):
    group_id: int


class MessageResponse(MessageBase):
    id: int
    created_at: datetime
    sender_id: int
    group_id: int
    sender: UserResponse

    class Config:
        from_attributes = True


# 令牌相关模型
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None