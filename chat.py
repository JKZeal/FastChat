import json
import datetime
from typing import Dict, Any, Optional, Union
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.websockets import WebSocketState  # Import WebSocketState
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from auth import SECRET_KEY, ALGORITHM
from db import Message, User, Group, user_group  # Import user_group for membership check


# Custom exception for connect failures that occur after websocket.accept()
class WebSocketConnectError(Exception):
    def __init__(self, message: str, code: int = status.WS_1008_POLICY_VIOLATION):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Dict[str, Any]] = {}
        self.connection_counter: int = 0

    async def connect(self, websocket: WebSocket, user: User, group_id: int, db: Session) -> int:
        # This method assumes websocket.accept() has been called by the endpoint
        # and will raise WebSocketConnectError if validation fails.

        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise WebSocketConnectError("群组不存在")

        # Efficient membership check using the association table
        is_member_stmt = user_group.select().where(
            user_group.c.user_id == user.id,
            user_group.c.group_id == group_id
        )
        is_member = db.execute(is_member_stmt).first()
        if not is_member:
            raise WebSocketConnectError("用户不在该群组中", code=status.WS_1003_UNSUPPORTED_DATA)

        self.connection_counter += 1
        connection_id = self.connection_counter
        self.active_connections[connection_id] = {
            "websocket": websocket,
            "user": user,
            "group_id": group_id
        }

        join_message_content = f"{user.username} 加入了聊天"
        await self.broadcast_to_group(
            group_id=group_id,
            message=json.dumps({
                "id": f"system-join-{datetime.datetime.now().timestamp()}-{user.id}",
                "content": join_message_content,
                "created_at": datetime.datetime.now().isoformat(),
                "message_type": "system",
                "sender": {"id": "system", "username": "系统消息"}  # System messages can have a conventional sender
            })
        )
        return connection_id

    async def disconnect(self, connection_id: int) -> None:
        if connection_id in self.active_connections:
            connection_details = self.active_connections.pop(connection_id)  # Use pop to remove
            user = connection_details["user"]
            group_id = connection_details["group_id"]

            # Check if there are other connections for this user in this group (e.g. multiple tabs)
            # This logic might be too complex if not needed. For now, assume one connection per user-group context.

            leave_message_content = f"{user.username} 离开了聊天"
            await self.broadcast_to_group(
                group_id=group_id,
                message=json.dumps({
                    "id": f"system-leave-{datetime.datetime.now().timestamp()}-{user.id}",
                    "content": leave_message_content,
                    "created_at": datetime.datetime.now().isoformat(),
                    "message_type": "system",
                    "sender": {"id": "system", "username": "系统消息"}
                })
            )
            print(f"User {user.username} disconnected from group {group_id}. Connection ID {connection_id} removed.")

    async def broadcast_to_group(self, group_id: int, message: str, skip_connection_id: Optional[int] = None) -> None:
        # Iterate over a copy of items in case the dictionary changes during iteration (though less likely here)
        for conn_id, connection in list(self.active_connections.items()):
            if connection["group_id"] == group_id:
                if skip_connection_id is not None and conn_id == skip_connection_id:
                    continue
                try:
                    # Check websocket state before sending
                    if connection["websocket"].client_state == WebSocketState.CONNECTED:
                        await connection["websocket"].send_text(message)
                    else:  # Stale connection, consider removing
                        print(f"Skipping broadcast to stale connection ID {conn_id}")
                        # Potentially schedule this connection for cleanup if it's persistently not connected
                except Exception as e:  # Catch broader exceptions during send
                    print(f"Error broadcasting message to connection ID {conn_id}: {str(e)}")
                    # Consider removing problematic connections here or marking them for removal

    def get_user_by_connection_id(self, connection_id: int) -> Union[User, None]:
        connection = self.active_connections.get(connection_id)
        return connection["user"] if connection else None


manager = ConnectionManager()


async def get_websocket_user(websocket: WebSocket, db: Session) -> User:
    token = websocket.query_params.get("token")
    credentials_exception = WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION, reason="认证失败")

    if not token:
        # Note: if we await websocket.close() here, the function might not return to the caller
        # to allow it to accept first. It's better to raise and let the main endpoint handle closing.
        raise credentials_exception  # Let endpoint handle closing after accept if needed

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:  # Check if user is active
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION, reason="用户未激活")
    return user


async def chat_websocket_endpoint(websocket: WebSocket, db: Session) -> None:
    user: Optional[User] = None
    connection_id: Optional[int] = None
    group_id_int: Optional[int] = None

    try:
        # Perform authentication and initial param checks BEFORE accept if they lead to immediate rejection
        # If these raise WebSocketDisconnect, it will be caught below.
        user = await get_websocket_user(websocket, db)

        group_id_str = websocket.query_params.get("group_id")
        if not group_id_str:
            raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION, reason="缺少群组ID")

        try:
            group_id_int = int(group_id_str)
        except ValueError:
            raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION, reason="无效的群组ID格式")

        # If initial checks pass, accept the connection
        await websocket.accept()

        # Now, try to fully connect the user to the group via the manager
        # This involves further DB checks (group existence, membership)
        try:
            connection_id = await manager.connect(websocket, user, group_id_int, db)
        except WebSocketConnectError as e:
            # This error happens AFTER accept, so we can send a message
            await websocket.send_text(json.dumps({"type": "connection_error", "error": e.message}))
            await websocket.close(code=e.code)  # Close with the code from the exception
            return  # Exit endpoint

        # Main message loop
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)  # Assume valid JSON for now, add try-except for robustness

            # Handle client-side "init" message if it's part of your protocol
            if message_data.get("type") == "init":
                await websocket.send_text(json.dumps({
                    "type": "init_confirm", "message": "连接已初始化",
                    "timestamp": datetime.datetime.now().isoformat()
                }))
                continue

            content = message_data.get("content", "").strip()
            if not content:  # Ignore empty messages or send an error
                await websocket.send_text(json.dumps({
                    "type": "message_error", "error": "消息内容不能为空",
                    "timestamp": datetime.datetime.now().isoformat()
                }))
                continue

            db_message = Message(
                content=content,
                sender_id=user.id,  # user is guaranteed to be non-None here
                group_id=group_id_int,  # group_id_int is guaranteed non-None
                message_type="text"  # Default to text for now, extend for file/image later
            )
            db.add(db_message)
            db.commit()
            db.refresh(db_message)

            # Construct sender object for the message
            # Ensure avatar_url is available on the user object or fetch if necessary
            # For simplicity, assuming user.avatar_url is populated
            sender_info = {
                "id": user.id,
                "username": user.username,
                "avatar_url": user.avatar_url,
                "status": user.status  # Assuming status is available
            }

            response_data = {
                "id": db_message.id,
                "content": db_message.content,
                "created_at": db_message.created_at.isoformat(),
                "sender_id": user.id,  # Redundant if sender object is present
                "group_id": group_id_int,
                "message_type": db_message.message_type,
                "sender": sender_info
            }
            await manager.broadcast_to_group(group_id_int, json.dumps(response_data))

    except WebSocketDisconnect as e:
        # This catches disconnects from get_websocket_user, param checks before accept,
        # or client disconnecting.
        print(f"WebSocket disconnected: Code {e.code}, Reason: {e.reason or 'N/A'}")
        if connection_id is not None:  # If connection was fully established
            await manager.disconnect(connection_id)
        # If websocket is not already closed by FastAPI/Starlette due to the exception
        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close(code=e.code)
            except RuntimeError:  # Handle cases where websocket might already be closed
                pass

    except json.JSONDecodeError:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_text(json.dumps({
                "type": "error", "error": "无效的JSON格式",
                "timestamp": datetime.datetime.now().isoformat()
            }))
        # Optionally close connection for malformed JSON if it's persistent

    except Exception as e:
        print(
            f"Unhandled WebSocket error for user {user.username if user else 'Unknown'} in group {group_id_int if group_id_int else 'Unknown'}: {str(e)}")
        if connection_id is not None:
            await manager.disconnect(connection_id)
        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except RuntimeError:
                pass
    finally:
        # If connection_id was assigned but an error occurred before normal disconnect
        if connection_id is not None and connection_id in manager.active_connections:
            print(f"Cleaning up connection {connection_id} due to error or unclean exit.")
            await manager.disconnect(connection_id)