import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Path, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from db import User, Message, Group, get_db, user_group
from schema import (
    UserCreate, UserResponse, Token, UserLogin, GroupCreate,
    GroupResponse, GroupDetailResponse, MessageCreate, MessageResponse,
    UserProfile, UserProfileUpdate
)

# 创建路由
router = APIRouter()


# 用户注册
@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """注册新用户"""
    # 检查用户名是否存在
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # 创建新用户
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        hashed_password=hashed_password,
        created_at=datetime.now(),
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# 用户登录
@router.post("/token", response_model=Token)
def login_for_access_token(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """用户登录获取令牌"""
    user = authenticate_user(db, user_credentials.username, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username
    }


# 获取当前用户信息
@router.get("/users/me/", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


# 更新用户档案
@router.put("/users/me/profile", response_model=UserResponse)
def update_user_profile(
        profile_data: UserProfileUpdate,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """更新用户头像和简介"""
    current_user.avatar_url = profile_data.avatar_url
    current_user.bio = profile_data.bio

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user


# 添加获取头像列表的API端点
@router.get("/avatar/list")
def get_avatar_list():
    """获取所有可用头像"""
    avatar_dir = "src/avatar"
    try:
        # 获取目录中的所有PNG文件
        avatar_files = [f"/avatar/{f}" for f in os.listdir(avatar_dir) if f.lower().endswith('.png')]
        return avatar_files
    except Exception as e:
        print(f"获取头像列表失败: {str(e)}")
        return []


# 搜索群组
@router.get("/groups/search", response_model=List[GroupResponse])
def search_groups(name: str = Query(None), db: Session = Depends(get_db)):
    """搜索群组"""
    query = db.query(Group)

    if name:
        query = query.filter(Group.name.ilike(f"%{name}%"))

    groups = query.limit(10).all()
    return groups


# 发送文本消息
@router.post("/messages/", response_model=MessageResponse)
def create_message(
        message: MessageCreate,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """创建新消息"""
    # 验证用户是否在群组中
    user_in_group = db.query(user_group).filter(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == message.group_id
    ).first()

    if not user_in_group:
        raise HTTPException(status_code=403, detail="User not in group")

    # 创建消息
    db_message = Message(
        content=message.content,
        message_type=message.message_type,
        sender_id=current_user.id,
        group_id=message.group_id,
        created_at=datetime.now()
    )

    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    return db_message


# 获取所有消息
@router.get("/messages/", response_model=List[MessageResponse])
def read_messages(
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """获取所有消息"""
    messages = db.query(Message).offset(skip).limit(limit).all()
    return messages


# 群组相关路由
@router.post("/groups/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
        group: GroupCreate,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """创建新群组"""
    # 检查同名群组
    existing_group = db.query(Group).filter(Group.name == group.name).first()
    if existing_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group with this name already exists"
        )

    # 创建群组
    db_group = Group(
        name=group.name,
        description=group.description,
        creator_id=current_user.id,
        created_at=datetime.now()
    )

    db.add(db_group)
    db.commit()
    db.refresh(db_group)

    # 将创建者添加到群组
    stmt = user_group.insert().values(
        user_id=current_user.id,
        group_id=db_group.id,
        joined_at=datetime.now()
    )
    db.execute(stmt)
    db.commit()

    return db_group


@router.get("/groups/", response_model=List[GroupResponse])
def read_user_groups(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """获取用户所在的所有群组"""
    # 获取用户所在的群组
    groups = db.query(Group).join(
        user_group,
        user_group.c.group_id == Group.id
    ).filter(
        user_group.c.user_id == current_user.id
    ).all()

    return groups


@router.get("/groups/{group_id}", response_model=GroupDetailResponse)
def get_group_details(
        group_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """获取群组详情"""
    # 检查群组是否存在
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # 检查用户是否在群组中
    user_in_group = db.query(user_group).filter(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    ).first()

    if not user_in_group:
        raise HTTPException(status_code=403, detail="User not in group")

    return group


@router.post("/groups/{group_id}/join", response_model=GroupDetailResponse)
def join_group(
        group_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """加入群组"""
    # 检查群组是否存在
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # 检查是否已在群组中
    user_in_group = db.query(user_group).filter(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    ).first()

    if not user_in_group:
        # 加入群组
        stmt = user_group.insert().values(
            user_id=current_user.id,
            group_id=group_id,
            joined_at=datetime.now()
        )
        db.execute(stmt)
        db.commit()

    return group


@router.post("/groups/{group_id}/leave")
def leave_group(
        group_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """离开群组"""
    # 检查群组是否存在
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # 检查是否在群组中
    user_in_group = db.query(user_group).filter(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    ).first()

    if not user_in_group:
        raise HTTPException(status_code=403, detail="User not in group")

    # 如果是创建者，不允许离开
    if group.creator_id == current_user.id:
        raise HTTPException(status_code=400, detail="Creator cannot leave group")

    # 离开群组
    stmt = user_group.delete().where(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    )
    db.execute(stmt)
    db.commit()

    return {"message": "Left group successfully"}


# 群组消息相关路由
@router.post("/groups/{group_id}/messages/", response_model=MessageResponse)
def create_group_message(
        group_id: int,
        message: MessageCreate,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """在群组中发送消息"""
    # 验证用户是否在群组中
    user_in_group = db.query(user_group).filter(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    ).first()

    if not user_in_group:
        raise HTTPException(status_code=403, detail="User not in group")

    # 创建消息
    db_message = Message(
        content=message.content,
        message_type=message.message_type,
        sender_id=current_user.id,
        group_id=group_id,
        created_at=datetime.now()
    )

    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    return db_message


@router.get("/groups/{group_id}/messages/", response_model=List[MessageResponse])
def read_group_messages(
        group_id: int,
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """获取群组消息"""
    # 验证用户是否在群组中
    user_in_group = db.query(user_group).filter(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    ).first()

    if not user_in_group:
        raise HTTPException(status_code=403, detail="User not in group")

    # 获取消息
    messages = db.query(Message).filter(
        Message.group_id == group_id
    ).order_by(
        Message.created_at.asc()
    ).offset(skip).limit(limit).all()

    return messages


# 文件访问路由
@router.get("/uploads/{file_path:path}")
def get_file(file_path: str):
    """获取上传的文件"""
    file_location = f"uploads/{file_path}"
    if not os.path.isfile(file_location):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_location)