import os
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from chat import chat_websocket_endpoint
from db import get_db, init_db
from router import router


# 定义 lifespan 处理函数
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行的代码
    print("应用启动...")
    print("初始化数据库...")
    init_db()  # 确保数据库初始化

    # 创建上传目录
    os.makedirs("uploads/avatars", exist_ok=True)
    os.makedirs("uploads/files", exist_ok=True)
    os.makedirs("uploads/images", exist_ok=True)
    print("上传目录已创建")

    print("数据库初始化完成")
    # 其他启动逻辑，例如初始化连接池、缓存等
    yield
    # 关闭时执行的代码
    print("应用关闭...")
    # 其他清理逻辑，例如关闭连接池、保存状态等


# 创建 FastAPI 应用实例，指定 lifespan
app = FastAPI(
    title="FastChat API",
    description="小型网络聊天室API",
    lifespan=lifespan  # 添加 lifespan 参数
)

# 添加 CORS 中间件
app.add_middleware(
    cast(Any, CORSMiddleware),  # 使用cast解决类型检查问题
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(router, prefix="/api")  # 为API路由添加前缀


# 添加 WebSocket 路由
@app.websocket("/ws/chat")
async def websocket_endpoint(
        websocket: WebSocket,
        db: Session = Depends(get_db)
):
    await chat_websocket_endpoint(websocket, db)


# 定义首页路由
@app.get("/")
async def root():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse(content={
            "message": "欢迎使用MoeChat API",
            "note": "前端文件未找到，请确保项目根目录下有index.html"
        })


# 运行应用
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)