import os
import shutil
import uuid
from fastapi import UploadFile, HTTPException, status
from typing import Optional

# 上传文件保存目录
UPLOAD_DIR = "uploads"
AVATAR_DIR = os.path.join(UPLOAD_DIR, "avatars")
FILE_DIR = os.path.join(UPLOAD_DIR, "files")
IMAGE_DIR = os.path.join(UPLOAD_DIR, "images")

# 确保目录存在
os.makedirs(AVATAR_DIR, exist_ok=True)
os.makedirs(FILE_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# 允许的图片文件格式
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

# 允许上传的文件大小限制 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


async def save_upload_file(upload_file: UploadFile, directory: str) -> str:
    """保存上传的文件并返回相对路径"""
    # 检查文件大小
    content = await upload_file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="文件太大。最大允许大小为10MB"
        )

    # 生成唯一文件名
    file_ext = os.path.splitext(upload_file.filename)[1] if upload_file.filename else ""
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(directory, unique_filename)

    # 写入文件
    with open(file_path, "wb") as f:
        f.write(content)

    # 返回相对URL路径
    relative_path = os.path.join(os.path.basename(directory), unique_filename)
    return relative_path.replace("\\", "/")  # 确保URL路径使用正斜杠


async def save_avatar(avatar: UploadFile) -> str:
    """保存用户头像"""
    if avatar.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持JPEG、PNG、GIF和WebP格式的图片"
        )
    return await save_upload_file(avatar, AVATAR_DIR)


async def save_image_message(image: UploadFile) -> str:
    """保存聊天图片消息"""
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持JPEG、PNG、GIF和WebP格式的图片"
        )
    return await save_upload_file(image, IMAGE_DIR)


async def save_file_message(file: UploadFile) -> str:
    """保存聊天文件消息"""
    return await save_upload_file(file, FILE_DIR)


def get_file_url(file_path: str) -> str:
    """获取文件的URL路径"""
    return f"/uploads/{file_path}"