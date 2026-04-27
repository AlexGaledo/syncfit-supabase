"""
Socials API endpoints
- Connections: send, list, respond (accept/decline/block), remove
- Conversations: create, list, get, participant management
- Messages: send, paginated history, edit, delete
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from typing import Any, List, Optional, cast
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, get_current_db_user
from app.models.user import User, Trainer_info, User_Profile
from app.models.social import (
    Connections, ConnectionStatus as ConnectionStatusModel,
    Conversations, ConversationType as ConversationTypeModel,
    Conversation_Participants, ConversationRole as ConversationRoleModel,
    Messages, MessageType as MessageTypeModel, 
    ConnectionType
    
)

from app.schemas.social import (
    ConnectionStatus, ConnectionResponse,
    ConversationType, ConversationResponse, ConversationCreate, ConversationUpdate,
    ConversationParticipantResponse,
    MessageType, MessageCreate, MessageUpdate, MessageResponse,
    PaginatedMessages, PaginatedConversations, TrainerInfoResponse,
)

socials_router = APIRouter(prefix="/socials", tags=["Socials"])


# ============================================================================
# HELPERS
# ============================================================================

def _get_connection_or_404(db: Session, connection_id: UUID) -> Connections:
    conn = db.query(Connections).filter(Connections.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return conn


def _get_conversation_or_404(db: Session, conversation_id: UUID) -> Conversations:
    conv = (
        db.query(Conversations)
        .options(joinedload(Conversations.participants))
        .filter(Conversations.id == conversation_id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


def _assert_participant(conv: Conversations, user_id: UUID) -> Conversation_Participants:
    """Raises 403 if the user is not an active participant of the conversation."""
    part = next(
        (p for p in conv.participants if p.user_id == user_id and p.is_active),
        None
    )
    if not part:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant of this conversation")
    return part


def _assert_admin_participant(conv: Conversations, user_id: UUID) -> None:
    """Raises 403 if the user is not an admin participant of the conversation."""
    part = _assert_participant(conv, user_id)
    part_role = cast(ConversationRoleModel, part.role)
    if part_role != ConversationRoleModel.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conversation admin access required")


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
    current_user_id = cast(UUID, current_db_user.id)

    if current_user_id == addressee_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot connect with yourself")

    addressee = db.query(User).filter(User.id == addressee_id).first()
    if not addressee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check for an existing connection in either direction
    existing = db.query(Connections).filter(
        (
            (Connections.requester_id == current_user_id) & (Connections.addressee_id == addressee_id)
        ) | (
            (Connections.requester_id == addressee_id) & (Connections.addressee_id == current_user_id)
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A connection already exists with status '{existing.status.value}'"
        )

    conn = Connections(requester_id=current_user_id, addressee_id=addressee_id)
    db.add(conn)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connection request already sent")
    db.refresh(conn)
    return conn


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
    current_user_id = cast(UUID, current_db_user.id)

    query = db.query(Connections).filter(
        (Connections.requester_id == current_user_id) |
        (Connections.addressee_id == current_user_id)
    )
    if connection_status:
        query = query.filter(Connections.status == connection_status.value)

    return query.order_by(Connections.created_at.desc()).offset(skip).limit(limit).all()


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
    conn = _get_connection_or_404(db, connection_id)
    current_user_id = cast(UUID, current_db_user.id)

    is_addressee = cast(UUID, conn.addressee_id) == current_user_id
    is_requester = cast(UUID, conn.requester_id) == current_user_id

    if not (is_addressee or is_requester):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your connection")

    # Only addressee can accept or decline; either party can block
    if new_status in (ConnectionStatus.accepted, ConnectionStatus.declined) and not is_addressee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the recipient can accept or decline a connection request"
        )

    setattr(conn, "status", ConnectionStatusModel[new_status.value])
    db.commit()
    db.refresh(conn)
    return conn


@socials_router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """
    Remove a connection. Either party may remove it.
    """
    conn = _get_connection_or_404(db, connection_id)
    current_user_id = cast(UUID, current_db_user.id)

    if cast(UUID, conn.requester_id) != current_user_id and cast(UUID, conn.addressee_id) != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your connection")

    db.delete(conn)
    db.commit()
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
    current_user_id = cast(UUID, current_db_user.id)

    # Collect all participant IDs including creator
    all_participant_ids = list(set([current_user_id] + list(data.participant_ids)))

    if data.type == ConversationType.direct:
        if len(all_participant_ids) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Direct conversations must have exactly 2 participants"
            )
        # Guard duplicate DM: check if a direct conversation already exists between these two users
        other_id = next(pid for pid in all_participant_ids if pid != current_user_id)
        existing_dm = (
            db.query(Conversations)
            .join(Conversation_Participants, Conversation_Participants.conversation_id == Conversations.id)
            .filter(
                Conversations.type == ConversationTypeModel.direct,
                Conversation_Participants.user_id == current_user_id,
                Conversation_Participants.is_active == True,
            )
            .all()
        )
        for conv in existing_dm:
            other_participant_ids = {cast(UUID, p.user_id) for p in conv.participants if cast(UUID, p.user_id) != current_user_id}
            if other_id in other_participant_ids:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A direct conversation with this user already exists"
                )

    if data.type == ConversationType.group and not data.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group conversations require a name"
        )

    # Verify all participant users exist
    for pid in all_participant_ids:
        if not db.query(User).filter(User.id == pid).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {pid} not found")

    conv = Conversations(
        type=ConversationTypeModel[data.type.value],
        name=data.name,
        creator_id=current_user_id,
    )
    db.add(conv)
    db.flush()

    for pid in all_participant_ids:
        role = ConversationRoleModel.admin if pid == current_user_id else ConversationRoleModel.member
        db.add(Conversation_Participants(conversation_id=conv.id, user_id=pid, role=role))

    db.commit()
    db.refresh(conv)
    return conv


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
    skip = (page - 1) * page_size
    current_user_id = cast(UUID, current_db_user.id)

    base_query = (
        db.query(Conversations)
        .join(Conversation_Participants, Conversation_Participants.conversation_id == Conversations.id)
        .filter(
            Conversation_Participants.user_id == current_user_id,
            Conversation_Participants.is_active == True,
        )
        .options(
            joinedload(Conversations.participants),
            joinedload(Conversations.last_message),
        )
        .order_by(Conversations.last_message_at.desc().nullslast())
    )

    total = base_query.count()
    conversations = base_query.offset(skip).limit(page_size).all()

    return PaginatedConversations(
        conversations=cast(List[ConversationResponse], conversations),
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + len(conversations)) < total,
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
    conv = _get_conversation_or_404(db, conversation_id)
    _assert_participant(conv, cast(UUID, current_db_user.id))
    return conv


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
    conv = _get_conversation_or_404(db, conversation_id)
    _assert_admin_participant(conv, cast(UUID, current_db_user.id))

    if data.name is not None:
        setattr(conv, "name", data.name)

    db.commit()
    db.refresh(conv)
    return conv


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
    conv = _get_conversation_or_404(db, conversation_id)
    _assert_admin_participant(conv, cast(UUID, current_db_user.id))

    if cast(ConversationTypeModel, conv.type) == ConversationTypeModel.direct:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add participants to a direct conversation"
        )

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = next((p for p in conv.participants if p.user_id == user_id), None)
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a participant")
        # Re-activate if they previously left
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    part = Conversation_Participants(
        conversation_id=conversation_id,
        user_id=user_id,
        role=ConversationRoleModel.member,
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


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
    conv = _get_conversation_or_404(db, conversation_id)
    current_user_id = cast(UUID, current_db_user.id)
    caller_part = _assert_participant(conv, current_user_id)

    is_self = user_id == current_user_id
    is_admin = cast(ConversationRoleModel, caller_part.role) == ConversationRoleModel.admin

    if not (is_self or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can remove other participants")

    target_part = next((p for p in conv.participants if p.user_id == user_id and p.is_active), None)
    if not target_part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    target_part.is_active = False
    db.commit()
    return None


# ============================================================================
# MESSAGES ENDPOINTS (x)
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
    from sqlalchemy.sql import func as sqlfunc

    conv = _get_conversation_or_404(db, conversation_id)
    current_user_id = cast(UUID, current_db_user.id)
    _assert_participant(conv, current_user_id)

    if data.reply_to_id:
        reply_target = db.query(Messages).filter(
            Messages.id == data.reply_to_id,
            Messages.conversation_id == conversation_id,
        ).first()
        if not reply_target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reply target message not found")

    msg = Messages(
        conversation_id=conversation_id,
        sender_id=current_user_id,
        content=data.content,
        type=MessageTypeModel[data.type.value],
        reply_to_id=data.reply_to_id,
    )
    db.add(msg)
    db.flush()

    # Update conversation's last message pointer
    conv.last_message_at = msg.created_at
    conv.last_message_id = msg.id

    db.commit()
    db.refresh(msg)
    return msg


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
    conv = _get_conversation_or_404(db, conversation_id)
    _assert_participant(conv, cast(UUID, current_db_user.id))

    query = db.query(Messages).filter(Messages.conversation_id == conversation_id)

    if before_id:
        cursor_msg = db.query(Messages).filter(Messages.id == before_id).first()
        if cursor_msg:
            query = query.filter(Messages.created_at < cursor_msg.created_at)

    total = query.count()
    skip = (page - 1) * page_size if not before_id else 0
    messages = query.order_by(Messages.created_at.desc()).offset(skip).limit(page_size).all()

    return PaginatedMessages(
        messages=list(reversed(messages)),  # return chronological order
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + len(messages)) < total,
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
    conv = _get_conversation_or_404(db, conversation_id)
    current_user_id = cast(UUID, current_db_user.id)
    _assert_participant(conv, current_user_id)

    msg = db.query(Messages).filter(
        Messages.id == message_id,
        Messages.conversation_id == conversation_id,
    ).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    if cast(UUID, msg.sender_id) != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit your own messages")

    setattr(msg, "content", data.content)
    setattr(msg, "is_edited", True)

    db.commit()
    db.refresh(msg)
    return msg


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
    conv = _get_conversation_or_404(db, conversation_id)
    current_user_id = cast(UUID, current_db_user.id)
    caller_part = _assert_participant(conv, current_user_id)

    msg = db.query(Messages).filter(
        Messages.id == message_id,
        Messages.conversation_id == conversation_id,
    ).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    is_sender = cast(UUID, msg.sender_id) == current_user_id
    is_admin = cast(ConversationRoleModel, caller_part.role) == ConversationRoleModel.admin

    if not (is_sender or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this message")

    db.delete(msg)
    db.commit()
    return None


@socials_router.get('/get-connected-trainers')
async def get_connected_trainers(
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user)
):
    try:
        # retrieve connected trainers first 
        connected_trainers = db.query(Connections).filter(
            or_(Connections.addressee_id == current_db_user.id, Connections.requester_id == current_db_user.id),
            Connections.connection_type == ConnectionType.trainership,
            Connections.status == ConnectionStatusModel.accepted
        ).all()

        # retrieve info for each trainers
        connected_trainers_info = []

        for trainer in connected_trainers:
            trainer_id = trainer.requester_id if trainer.addressee_id == current_db_user.id else trainer.addressee_id #type:ignore
            trainer_info = db.query(Trainer_info).filter(Trainer_info.user_id == trainer_id).first()
            if trainer_info:
                connected_trainers_info.append(trainer_info)

        return connected_trainers_info
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'something went wrong in the get-connected-trainers endpoint: {e}')


@socials_router.get('/get-trainer-info/{user_id}', response_model=TrainerInfoResponse)
async def get_trainer_info(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_db_user: User = Depends(get_current_db_user),
):
    """Get trainer profile info by trainer user ID."""
    trainer_info = db.query(Trainer_info).filter(Trainer_info.user_id == user_id).first()
    if not trainer_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer info not found")
        
    trainer_user_info: User = trainer_info.user
    traiter_user_profile: User_Profile = trainer_user_info.profile

    if not trainer_user_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer user info not found")
    
    return {"trainer_info": trainer_info,
            "trainer_profile": traiter_user_profile}




# ============================================================================
# WebSocket Manager
# ============================================================================

from fastapi import WebSocket, WebSocketDisconnect, WebSocketException
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: Dict[str, List[WebSocket]] = {}


    async def connect(self, websocket: WebSocket, room_id:str):
        await websocket.accept()
        self.rooms.setdefault(room_id, []).append(websocket)


    def disconnect(self, websocket: WebSocket, room_id:str):
        self.rooms.get(room_id, []).remove(websocket)


    async def broadcast(self, room_id:str, message: Dict):
        for ws in self.rooms.get(room_id, []):
            await ws.send_text(json.dumps(message))

connection = ConnectionManager()

@socials_router.websocket('/ws/{room_id}/{user_id}')
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    user_id:str
):
    await connection.connect(websocket=websocket, room_id=room_id)
    try:
        while True:
            data = await websocket.receive_text()
            await connection.broadcast(room_id,{
                "user": user_id,
                "text": data
            })
    except WebSocketDisconnect:
        connection.disconnect(websocket=websocket,room_id=room_id)
