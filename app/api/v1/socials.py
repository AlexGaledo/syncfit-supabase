"""
Socials API endpoints
- Connections: send, list, respond (accept/decline/block), remove
- Conversations: create, list, get, participant management
- Messages: send, paginated history, edit, delete
"""
import json
import logging
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_current_db_user
from app.models.user import User
from app.schemas.social import (
    ConnectionResponse,
    ConnectionStatus,
    ConversationCreate,
    ConversationParticipantResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
    MessageUpdate,
    PaginatedConversations,
    PaginatedMessages,
    TrainerInfoResponse,
)
from app.services import social_service


logger = logging.getLogger(__name__)

socials_router = APIRouter(prefix="/socials", tags=["Socials"])


# ============================================================================
# CONNECTIONS ENDPOINTS
# ============================================================================

@socials_router.post("/connections", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def send_connection_request(
    addressee_id: UUID,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Send a connection request to another user.
    """
    return social_service.send_connection_request(
        db, cast(UUID, current_db_user.id), addressee_id
    )


@socials_router.get("/connections", response_model=List[ConnectionResponse])
async def get_my_connections(
    connection_status: Optional[ConnectionStatus] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    List current user's connections. Optionally filter by status (pending/accepted/declined/blocked).
    Returns connections where the user is either the requester or addressee.
    """
    return social_service.list_my_connections(
        db, cast(UUID, current_db_user.id), connection_status, skip, limit
    )


@socials_router.patch("/connections/{connection_id}", response_model=ConnectionResponse)
async def respond_to_connection(
    connection_id: UUID,
    new_status: ConnectionStatus,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Accept, decline, or block a connection request.
    Only the addressee (recipient) may respond to a pending request.
    Either party may block.
    """
    return social_service.respond_to_connection(
        db, cast(UUID, current_db_user.id), connection_id, new_status
    )


@socials_router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Remove a connection. Either party may remove it.
    """
    social_service.remove_connection(db, cast(UUID, current_db_user.id), connection_id)
    return None


# ============================================================================
# CONVERSATIONS ENDPOINTS
# ============================================================================

@socials_router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Create a direct or group conversation.
    For direct conversations, prevents duplicate DM pairs.
    The creator is automatically added as an admin participant.
    """
    return social_service.create_conversation(db, cast(UUID, current_db_user.id), data)


@socials_router.get("/conversations", response_model=PaginatedConversations)
async def get_my_conversations(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    List all conversations the current user participates in, ordered by most recent message.
    """
    return social_service.list_my_conversations(
        db, cast(UUID, current_db_user.id), page, page_size
    )


@socials_router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Get a conversation's details and participant list.
    """
    return social_service.get_conversation(
        db, cast(UUID, current_db_user.id), conversation_id
    )


@socials_router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Update conversation metadata (e.g. rename a group chat). Admin only.
    """
    return social_service.update_conversation(
        db, cast(UUID, current_db_user.id), conversation_id, data
    )


# ============================================================================
# PARTICIPANTS ENDPOINTS
# ============================================================================

@socials_router.post(
    "/conversations/{conversation_id}/participants",
    response_model=ConversationParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_participant(
    conversation_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Add a user to a group conversation. Conversation admin only.
    """
    return social_service.add_participant(
        db, cast(UUID, current_db_user.id), conversation_id, user_id
    )


@socials_router.delete(
    "/conversations/{conversation_id}/participants/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_participant(
    conversation_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Remove a participant from a group conversation, or leave yourself.
    Admins can remove others; any participant can remove themselves.
    """
    social_service.remove_participant(
        db, cast(UUID, current_db_user.id), conversation_id, user_id
    )
    return None


# ============================================================================
# MESSAGES ENDPOINTS
# ============================================================================

@socials_router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: UUID,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Send a message in a conversation. Optionally reply to an existing message.
    """
    return social_service.send_message(
        db, cast(UUID, current_db_user.id), conversation_id, data
    )


@socials_router.get(
    "/conversations/{conversation_id}/messages",
    response_model=PaginatedMessages,
)
async def get_messages(
    conversation_id: UUID,
    page: int = 1,
    page_size: int = 30,
    before_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Get paginated message history for a conversation.
    Use `before_id` for cursor-based pagination (pass the oldest message ID you have
    to load earlier messages). Falls back to offset pagination via `page` if omitted.
    """
    return social_service.list_messages(
        db, cast(UUID, current_db_user.id), conversation_id, page, page_size, before_id
    )


@socials_router.patch(
    "/conversations/{conversation_id}/messages/{message_id}",
    response_model=MessageResponse,
)
async def edit_message(
    conversation_id: UUID,
    message_id: UUID,
    data: MessageUpdate,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Edit a message. Only the original sender may edit.
    """
    return social_service.edit_message(
        db, cast(UUID, current_db_user.id), conversation_id, message_id, data
    )


@socials_router.delete(
    "/conversations/{conversation_id}/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_message(
    conversation_id: UUID,
    message_id: UUID,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Delete a message. The sender or a conversation admin may delete.
    """
    social_service.delete_message(
        db, cast(UUID, current_db_user.id), conversation_id, message_id
    )
    return None


@socials_router.get('/get-connected-trainers')
async def get_connected_trainers(
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    return social_service.get_connected_trainers(db, current_db_user)


@socials_router.get('/get-connected-trainees')
async def get_connected_trainees(
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    return social_service.get_connected_trainees(db, current_db_user)


@socials_router.get('/get-trainer-info/{user_id}', response_model=TrainerInfoResponse)
async def get_trainer_info(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """Get trainer profile info by trainer user ID."""
    return social_service.get_trainer_info(db, user_id)


@socials_router.get('/get-my-conversations')
async def get_my_conversations_items(
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    return social_service.get_my_conversations_items(db, current_db_user)


@socials_router.get('/get-number-of-trainers', response_model=List[TrainerInfoResponse], status_code=status.HTTP_200_OK)
def get_trainers_limited(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    current_db_user: User = Depends(get_current_db_user),
):
    """retrieve number of trainers [10 at a time]"""
    return social_service.list_trainers_limited(db, current_db_user, skip, limit)


# ============================================================================
# WebSocket Manager
# ============================================================================

class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        self.rooms.setdefault(room_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        self.rooms.get(room_id, []).remove(websocket)

    async def broadcast(self, room_id: str, message: Dict):
        for ws in self.rooms.get(room_id, []):
            await ws.send_text(json.dumps(message))


connection = ConnectionManager()


@socials_router.websocket('/ws/{room_id}/{user_id}')
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    user_id: str,
):
    await connection.connect(websocket=websocket, room_id=room_id)
    try:
        while True:
            data = await websocket.receive_text()
            await connection.broadcast(room_id, {
                "user": user_id,
                "text": data,
            })
    except WebSocketDisconnect:
        connection.disconnect(websocket=websocket, room_id=room_id)
