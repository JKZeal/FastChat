import os
import asyncio
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from chat import chat_websocket_endpoint, manager
from db import get_db, init_db, SessionLocal
from router import router


# 定义 lifespan 处理函数
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时执行
    print("应用启动...")
    init_db()
    print("数据库初始化完成")
    yield
    print("应用关闭...")


# 创建 FastAPI 应用实例，指定 lifespan
app = FastAPI(
    title="FastChat API",
    description="网络聊天室API",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    cast(Any, CORSMiddleware),
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保目录存在
os.makedirs("src/avatar", exist_ok=True)

# 挂载静态文件目录
app.mount("/avatar", StaticFiles(directory="src/avatar"), name="avatar")

# 包含路由
app.include_router(router, prefix="/api")


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
    return JSONResponse(content={
        "message": "欢迎使用FastChat API"
    })


# 运行应用
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)