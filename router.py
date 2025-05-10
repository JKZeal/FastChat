from datetime import timedelta
from typing import List, Optional
import os

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import sqlalchemy.exc

from auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from db import User, Message, Group, get_db
from schema import (
    UserCreate, UserResponse, Token, UserLogin, GroupCreate, 
    GroupResponse, GroupDetailResponse, MessageCreate, MessageResponse,
    UserProfile, UserProfileUpdate
)
from upload import save_avatar, save_image_message, save_file_message, get_file_url

# 创建路由
router = APIRouter()


# 用户注册
@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """创建新用户"""
    # 检查用户名是否已存在
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username, 
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


# 用户登录
@router.post("/token", response_model=Token)
def login_for_access_token(user_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录获取令牌"""
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


# 获取当前用户信息
@router.get("/users/me/", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


# 更新用户档案
@router.put("/users/me/profile", response_model=UserResponse)
async def update_user_profile(
    status: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新用户档案"""
    # 更新头像
    if avatar:
        avatar_path = await save_avatar(avatar)
        current_user.avatar_url = get_file_url(avatar_path)
    
    # 更新状态
    if status is not None:
        current_user.status = status
    
    # 更新简介
    if bio is not None:
        current_user.bio = bio
    
    # 保存更改
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return current_user


# 搜索群组
# 搜索群组
@router.get("/groups/search", response_model=List[GroupResponse])
def search_groups(name: Optional[str] = None, id: Optional[int] = None, db: Session = Depends(get_db)):
    """根据名称或ID搜索群组"""
    if id is not None:
        # 通过ID精确查询
        group = db.query(Group).filter(Group.id == id).first()
        return [group] if group else []
    elif name:
        # 通过名称模糊查询
        groups = db.query(Group).filter(Group.name.ilike(f"%{name}%")).all()
        return groups
    else:
        # 未提供查询参数
        return []


# 发送文本消息
@router.post("/messages/", response_model=MessageResponse)
def create_message(
    message: MessageCreate, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """发送文本消息"""
    # 检查群组是否存在
    group = db.query(Group).filter(Group.id == message.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="群组不存在"
        )
    
    # 检查用户是否在群组中
    if current_user not in group.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该群组成员"
        )
    
    # 创建新消息
    db_message = Message(
        content=message.content,
        message_type=message.message_type,
        file_url=message.file_url,
        file_name=message.file_name,
        file_size=message.file_size,
        sender_id=current_user.id,
        group_id=message.group_id
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # 关联发送者
    db_message.sender = current_user
    
    return db_message


# 发送图片消息
@router.post("/messages/image", response_model=MessageResponse)
async def create_image_message(
    group_id: int = Form(...),
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """发送图片消息"""
    # 检查群组是否存在
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="群组不存在"
        )
    
    # 检查用户是否在群组中
    if current_user not in group.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该群组成员"
        )
    
    # 保存图片
    image_path = await save_image_message(image)
    file_url = get_file_url(image_path)
    
    # 创建新消息
    db_message = Message(
        content="[图片]",
        message_type="image",
        file_url=file_url,
        file_name=image.filename,
        file_size=os.path.getsize(os.path.join("uploads", image_path)) if os.path.exists(os.path.join("uploads", image_path)) else 0,
        sender_id=current_user.id,
        group_id=group_id
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # 关联发送者
    db_message.sender = current_user
    
    return db_message


# 发送文件消息
@router.post("/messages/file", response_model=MessageResponse)
async def create_file_message(
    group_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """发送文件消息"""
    # 检查群组是否存在
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="群组不存在"
        )
    
    # 检查用户是否在群组中
    if current_user not in group.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该群组成员"
        )
    
    # 保存文件
    file_path = await save_file_message(file)
    file_url = get_file_url(file_path)
    
    # 创建新消息
    db_message = Message(
        content=f"[文件] {file.filename}",
        message_type="file",
        file_url=file_url,
        file_name=file.filename,
        file_size=os.path.getsize(os.path.join("uploads", file_path)) if os.path.exists(os.path.join("uploads", file_path)) else 0,
        sender_id=current_user.id,
        group_id=group_id
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # 关联发送者
    db_message.sender = current_user
    
    return db_message


# 获取所有消息
@router.get("/messages/", response_model=List[MessageResponse])
def read_messages(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取用户的所有消息"""
    # 获取用户所在的所有群组的ID
    group_ids = [group.id for group in current_user.groups]
    
    # 获取这些群组中的所有消息
    messages = db.query(Message).filter(Message.group_id.in_(group_ids)).all()
    
    return messages


# 群组相关路由
@router.post("/groups/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group: GroupCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建新群组"""
    # 创建群组
    db_group = Group(
        name=group.name,
        description=group.description
    )
    
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    
    # 将创建者添加为群组成员
    db_group.members.append(current_user)
    db.commit()
    
    return db_group


@router.get("/groups/", response_model=List[GroupResponse])
def read_user_groups(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取当前用户所在的所有群组"""
    return current_user.groups


@router.get("/groups/{group_id}", response_model=GroupDetailResponse)
def read_group(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取群组详情"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="群组不存在"
        )
    
    return group


@router.post("/groups/{group_id}/join", response_model=GroupDetailResponse)
def join_group(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """加入群组"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="群组不存在"
        )
    
    # 检查用户是否已在群组中
    if current_user in group.members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经是该群组成员"
        )
    
    # 将用户添加到群组
    group.members.append(current_user)
    db.commit()
    db.refresh(group)
    
    return group


@router.post("/groups/{group_id}/leave")
def leave_group(
    group_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """退出群组"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="群组不存在"
        )
    
    # 检查用户是否在群组中
    if current_user not in group.members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您不是该群组成员"
        )
    
    # 将用户从群组中移除
    group.members.remove(current_user)
    db.commit()
    
    return {"detail": "已成功退出群组"}


# 群组消息相关路由
@router.post("/groups/{group_id}/messages/", response_model=MessageResponse)
def create_group_message(
    group_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """在特定群组中发送消息"""
    # 检查群组是否存在
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="群组不存在"
        )
    
    # 检查用户是否在群组中
    if current_user not in group.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该群组成员"
        )
    
    # 创建新消息
    db_message = Message(
        content=message.content,
        message_type=message.message_type,
        file_url=message.file_url,
        file_name=message.file_name,
        file_size=message.file_size,
        sender_id=current_user.id,
        group_id=group_id
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # 关联发送者
    db_message.sender = current_user
    
    return db_message


@router.get("/groups/{group_id}/messages/", response_model=List[MessageResponse])
def read_group_messages(
    group_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取特定群组的消息"""
    # 检查群组是否存在
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="群组不存在"
        )
    
    # 检查用户是否在群组中
    if current_user not in group.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该群组成员"
        )
    
    # 获取消息
    messages = db.query(Message).filter(Message.group_id == group_id).order_by(Message.created_at).offset(skip).limit(limit).all()
    
    return messages


# 文件访问路由
@router.get("/uploads/{file_path:path}")
def get_upload_file(file_path: str = Path(...)):
    """获取上传的文件"""
    file_path = os.path.join("uploads", file_path)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    return FileResponse(file_path)