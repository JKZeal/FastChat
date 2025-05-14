from typing import Dict, Any, Optional, Union
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.websockets import WebSocketState
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from auth import SECRET_KEY, ALGORITHM
from db import Message, User, Group, user_group


class WebSocketConnectError(Exception):
    def __init__(self, message: str, code: int = status.WS_1008_POLICY_VIOLATION):
        self.message = message
        self.code = code
        super().__init__(message)


class ConnectionManager:
    def __init__(self):
        # 连接池：{connection_id: {"websocket": websocket, "user": user, "group_id": group_id}}
        self.active_connections = {}
        # 计数器用于生成唯一连接ID
        self.connection_id_counter = 0

    async def connect(self, websocket: WebSocket, user: User, group_id: int, db: Session) -> int:
        """添加新的WebSocket连接"""
        await websocket.accept()

        # 生成连接ID
        self.connection_id_counter += 1
        connection_id = self.connection_id_counter

        # 将连接添加到活跃连接池
        self.active_connections[connection_id] = {
            "websocket": websocket,
            "user": user,
            "group_id": group_id
        }

        print(f"已分配连接ID {connection_id} 给用户 {user.username}")

        # 通知群组有新用户加入
        await self.broadcast_to_group(
            group_id,
            f"{user.username} 进入了聊天室",
            skip_connection_id=connection_id
        )

        return connection_id

    async def disconnect(self, connection_id: int, db: Session = None) -> None:
        """处理连接断开"""
        if connection_id not in self.active_connections:
            return

        connection_info = self.active_connections[connection_id]
        user = connection_info["user"]
        group_id = connection_info["group_id"]

        print(f"用户 {user.username} 的连接ID {connection_id} 已断开")

        # 从连接池中移除
        del self.active_connections[connection_id]

        # 通知群组有用户离开
        await self.broadcast_to_group(
            group_id,
            f"{user.username} 离开了聊天室"
        )

    async def broadcast_to_group(self, group_id: int, message: str, skip_connection_id: Optional[int] = None) -> None:
        """向群组内的所有连接广播系统消息"""
        for conn_id, connection in self.active_connections.items():
            if skip_connection_id == conn_id:
                continue

            if connection["group_id"] == group_id:
                websocket = connection["websocket"]
                if websocket.client_state == WebSocketState.CONNECTED:
                    try:
                        await websocket.send_json({
                            "type": "system_message",
                            "content": message
                        })
                    except Exception as e:
                        print(f"发送消息到连接 {conn_id} 失败: {str(e)}")

    def get_user_by_connection_id(self, connection_id: int) -> Union[User, None]:
        """通过连接ID获取用户"""
        connection = self.active_connections.get(connection_id)
        if connection:
            return connection["user"]
        return None


# 全局连接管理器实例
manager = ConnectionManager()


async def get_websocket_user(websocket: WebSocket, db: Session) -> User:
    """从WebSocket请求中获取用户信息"""
    print(f"调试信息: 尝试通过token验证WebSocket用户 (来自 {websocket.client.host})")
    token = websocket.query_params.get("token")
    credentials_exception = WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION, reason="认证失败")

    if not token:
        raise WebSocketConnectError("缺少认证token", code=status.WS_1008_POLICY_VIOLATION)

    try:
        # 解码JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise WebSocketConnectError("无效的token", code=status.WS_1008_POLICY_VIOLATION)

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise WebSocketConnectError("用户不存在", code=status.WS_1008_POLICY_VIOLATION)

    if not user.is_active:
        raise WebSocketConnectError("用户已禁用", code=status.WS_1008_POLICY_VIOLATION)

    # 更新用户最后活动时间
    user.last_activity = None
    db.commit()

    print(f"WebSocket连接用户验证成功: {username}")
    return user


async def chat_websocket_endpoint(websocket: WebSocket, db: Session) -> None:
    """处理聊天WebSocket连接"""
    print(f"调试信息: WebSocket连接尝试: {websocket.client.host}:{websocket.client.port}")
    user = None
    connection_id = None
    group_id_int = None

    try:
        # 获取群组ID
        group_id = websocket.query_params.get("group_id")
        if not group_id:
            raise WebSocketConnectError("缺少群组ID")

        try:
            group_id_int = int(group_id)
        except ValueError:
            raise WebSocketConnectError("无效的群组ID")

        # 验证用户
        user = await get_websocket_user(websocket, db)

        # 验证群组是否存在
        group = db.query(Group).filter(Group.id == group_id_int).first()
        if not group:
            raise WebSocketConnectError("群组不存在")

        # 验证用户是否在群组中
        user_in_group = db.query(user_group).filter(
            user_group.c.user_id == user.id,
            user_group.c.group_id == group_id_int
        ).first()

        if not user_in_group:
            raise WebSocketConnectError("用户不在该群组中")

        print(f"用户 {user.username} 正在连接到群组 {group_id_int}")

        # 建立连接
        print(f"WebSocket已接受来自用户 {user.username} 的连接至群组 {group_id_int}")
        connection_id = await manager.connect(websocket, user, group_id_int, db)

        # 持续接收消息
        while True:
            message_data = await websocket.receive_json()

            # 处理不同类型的消息
            if message_data.get("type") == "chat_message":
                content = message_data.get("content", "").strip()

                if content and len(content) <= 1000:  # 限制消息长度
                    # 创建新消息并保存到数据库
                    new_message = Message(
                        content=content,
                        sender_id=user.id,
                        group_id=group_id_int,
                        message_type="text"
                    )
                    db.add(new_message)
                    db.commit()
                    db.refresh(new_message)

                    # 准备发送的消息数据
                    message_response = {
                        "id": new_message.id,
                        "content": new_message.content,
                        "created_at": new_message.created_at.isoformat(),
                        "sender_id": new_message.sender_id,
                        "group_id": new_message.group_id,
                        "message_type": new_message.message_type,
                        "sender": {
                            "id": user.id,
                            "username": user.username,
                            "avatar_url": user.avatar_url
                        }
                    }

                    # 广播消息到群组
                    for conn_id, connection in manager.active_connections.items():
                        if connection["group_id"] == group_id_int:
                            try:
                                await connection["websocket"].send_json({
                                    "type": "chat_message",
                                    "message": message_response
                                })
                            except Exception as e:
                                print(f"发送消息到连接 {conn_id} 失败: {str(e)}")

    except WebSocketDisconnect as e:
        print(f"WebSocket断开连接: 用户 {user.username if user else '未知'} (连接ID {connection_id})")
        # 处理连接断开
        if connection_id is not None:
            await manager.disconnect(connection_id, db)

    except WebSocketConnectError as e:
        print(f"WebSocket连接错误: {e.message}")
        # 尝试关闭连接
        try:
            await websocket.close(code=e.code, reason=e.message)
        except Exception:
            pass

    except Exception as e:
        print(f"WebSocket处理错误: {str(e)}")
        # 尝试关闭连接
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
        # 处理连接断开
        if connection_id is not None:
            await manager.disconnect(connection_id, db)

    finally:
        # 如果连接ID存在且连接依然在活跃连接列表中，确保断开
        if connection_id is not None and connection_id in manager.active_connections:
            await manager.disconnect(connection_id, db)