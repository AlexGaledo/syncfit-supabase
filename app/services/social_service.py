"""Socials domain logic. Connections, conversations, participants, messages, trainer info."""
import logging
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.social import (
    Connections,
    ConnectionStatus as ConnectionStatusModel,
    ConnectionType,
    Conversations,
    ConversationType as ConversationTypeModel,
    Conversation_Participants,
    ConversationRole as ConversationRoleModel,
    Messages,
    MessageType as MessageTypeModel,
)
from app.models.user import Trainer_info, User, User_Profile
from app.schemas.social import (
    ConnectionStatus,
    ConversationCreate,
    ConversationType,
    ConversationUpdate,
    MessageCreate,
    MessageUpdate,
    PaginatedConversations,
    PaginatedMessages,
    ConversationResponse,
)


logger = logging.getLogger(__name__)


# ---- Helpers ----

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
        None,
    )
    if not part:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant of this conversation",
        )
    return part


def _assert_admin_participant(conv: Conversations, user_id: UUID) -> None:
    """Raises 403 if the user is not an admin participant of the conversation."""
    part = _assert_participant(conv, user_id)
    part_role = cast(ConversationRoleModel, part.role)
    if part_role != ConversationRoleModel.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conversation admin access required",
        )


# ---- Connections ----

def send_connection_request(db: Session, current_user_id: UUID, addressee_id: UUID) -> Connections:
    if current_user_id == addressee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot connect with yourself",
        )

    addressee = db.query(User).filter(User.id == addressee_id).first()
    if not addressee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = db.query(Connections).filter(
        (
            (Connections.requester_id == current_user_id)
            & (Connections.addressee_id == addressee_id)
        )
        | (
            (Connections.requester_id == addressee_id)
            & (Connections.addressee_id == current_user_id)
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A connection already exists with status '{existing.status.value}'",
        )

    conn = Connections(requester_id=current_user_id, addressee_id=addressee_id)
    db.add(conn)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Connection request already sent",
        )
    db.refresh(conn)
    return conn


def list_my_connections(
    db: Session,
    current_user_id: UUID,
    connection_status: Optional[ConnectionStatus],
    skip: int,
    limit: int,
) -> List[Connections]:
    query = db.query(Connections).filter(
        (Connections.requester_id == current_user_id)
        | (Connections.addressee_id == current_user_id)
    )
    if connection_status:
        query = query.filter(Connections.status == connection_status.value)

    return query.order_by(Connections.created_at.desc()).offset(skip).limit(limit).all()


def respond_to_connection(
    db: Session,
    current_user_id: UUID,
    connection_id: UUID,
    new_status: ConnectionStatus,
) -> Connections:
    conn = _get_connection_or_404(db, connection_id)

    is_addressee = cast(UUID, conn.addressee_id) == current_user_id
    is_requester = cast(UUID, conn.requester_id) == current_user_id

    if not (is_addressee or is_requester):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your connection")

    if new_status in (ConnectionStatus.accepted, ConnectionStatus.declined) and not is_addressee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the recipient can accept or decline a connection request",
        )

    setattr(conn, "status", ConnectionStatusModel[new_status.value])
    db.commit()
    db.refresh(conn)
    return conn


def remove_connection(db: Session, current_user_id: UUID, connection_id: UUID) -> None:
    conn = _get_connection_or_404(db, connection_id)

    if (
        cast(UUID, conn.requester_id) != current_user_id
        and cast(UUID, conn.addressee_id) != current_user_id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your connection")

    db.delete(conn)
    db.commit()


# ---- Conversations ----

def create_conversation(
    db: Session, current_user_id: UUID, data: ConversationCreate
) -> Conversations:
    all_participant_ids = list(set([current_user_id] + list(data.participant_ids)))

    if data.type == ConversationType.direct:
        if len(all_participant_ids) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Direct conversations must have exactly 2 participants",
            )
        other_id = next(pid for pid in all_participant_ids if pid != current_user_id)
        existing_dm = (
            db.query(Conversations)
            .join(
                Conversation_Participants,
                Conversation_Participants.conversation_id == Conversations.id,
            )
            .filter(
                Conversations.type == ConversationTypeModel.direct,
                Conversation_Participants.user_id == current_user_id,
                Conversation_Participants.is_active == True,
            )
            .all()
        )
        for conv in existing_dm:
            other_participant_ids = {
                cast(UUID, p.user_id)
                for p in conv.participants
                if cast(UUID, p.user_id) != current_user_id
            }
            if other_id in other_participant_ids:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A direct conversation with this user already exists",
                )

    if data.type == ConversationType.group and not data.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group conversations require a name",
        )

    for pid in all_participant_ids:
        if not db.query(User).filter(User.id == pid).first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"User {pid} not found"
            )

    conv = Conversations(
        type=ConversationTypeModel[data.type.value],
        name=data.name,
        creator_id=current_user_id,
    )
    db.add(conv)
    db.flush()

    for pid in all_participant_ids:
        role = (
            ConversationRoleModel.admin
            if pid == current_user_id
            else ConversationRoleModel.member
        )
        db.add(
            Conversation_Participants(
                conversation_id=conv.id, user_id=pid, role=role
            )
        )

    db.commit()
    db.refresh(conv)
    return conv


def list_my_conversations(
    db: Session, current_user_id: UUID, page: int, page_size: int
) -> PaginatedConversations:
    skip = (page - 1) * page_size

    base_query = (
        db.query(Conversations)
        .join(
            Conversation_Participants,
            Conversation_Participants.conversation_id == Conversations.id,
        )
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


def get_conversation(db: Session, current_user_id: UUID, conversation_id: UUID) -> Conversations:
    conv = _get_conversation_or_404(db, conversation_id)
    _assert_participant(conv, current_user_id)
    return conv


def update_conversation(
    db: Session,
    current_user_id: UUID,
    conversation_id: UUID,
    data: ConversationUpdate,
) -> Conversations:
    conv = _get_conversation_or_404(db, conversation_id)
    _assert_admin_participant(conv, current_user_id)

    if data.name is not None:
        setattr(conv, "name", data.name)

    db.commit()
    db.refresh(conv)
    return conv


# ---- Participants ----

def add_participant(
    db: Session, current_user_id: UUID, conversation_id: UUID, user_id: UUID
) -> Conversation_Participants:
    conv = _get_conversation_or_404(db, conversation_id)
    _assert_admin_participant(conv, current_user_id)

    if cast(ConversationTypeModel, conv.type) == ConversationTypeModel.direct:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add participants to a direct conversation",
        )

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = next((p for p in conv.participants if p.user_id == user_id), None)
    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a participant",
            )
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


def remove_participant(
    db: Session, current_user_id: UUID, conversation_id: UUID, user_id: UUID
) -> None:
    conv = _get_conversation_or_404(db, conversation_id)
    caller_part = _assert_participant(conv, current_user_id)

    is_self = user_id == current_user_id
    is_admin = cast(ConversationRoleModel, caller_part.role) == ConversationRoleModel.admin

    if not (is_self or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove other participants",
        )

    target_part = next(
        (p for p in conv.participants if p.user_id == user_id and p.is_active), None
    )
    if not target_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found"
        )

    target_part.is_active = False
    db.commit()


# ---- Messages ----

def send_message(
    db: Session, current_user_id: UUID, conversation_id: UUID, data: MessageCreate
) -> Messages:
    conv = _get_conversation_or_404(db, conversation_id)
    _assert_participant(conv, current_user_id)

    if data.reply_to_id:
        reply_target = (
            db.query(Messages)
            .filter(
                Messages.id == data.reply_to_id,
                Messages.conversation_id == conversation_id,
            )
            .first()
        )
        if not reply_target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reply target message not found",
            )

    msg = Messages(
        conversation_id=conversation_id,
        sender_id=current_user_id,
        content=data.content,
        type=MessageTypeModel[data.type.value],
        reply_to_id=data.reply_to_id,
    )
    db.add(msg)
    db.flush()

    conv.last_message_at = msg.created_at
    conv.last_message_id = msg.id

    db.commit()
    db.refresh(msg)
    return msg


def list_messages(
    db: Session,
    current_user_id: UUID,
    conversation_id: UUID,
    page: int,
    page_size: int,
    before_id: Optional[UUID],
) -> PaginatedMessages:
    conv = _get_conversation_or_404(db, conversation_id)
    _assert_participant(conv, current_user_id)

    query = db.query(Messages).filter(Messages.conversation_id == conversation_id)

    if before_id:
        cursor_msg = db.query(Messages).filter(Messages.id == before_id).first()
        if cursor_msg:
            query = query.filter(Messages.created_at < cursor_msg.created_at)

    total = query.count()
    skip = (page - 1) * page_size if not before_id else 0
    messages = (
        query.order_by(Messages.created_at.desc()).offset(skip).limit(page_size).all()
    )

    return PaginatedMessages(
        messages=list(reversed(messages)),
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + len(messages)) < total,
    )


def edit_message(
    db: Session,
    current_user_id: UUID,
    conversation_id: UUID,
    message_id: UUID,
    data: MessageUpdate,
) -> Messages:
    conv = _get_conversation_or_404(db, conversation_id)
    _assert_participant(conv, current_user_id)

    msg = (
        db.query(Messages)
        .filter(
            Messages.id == message_id,
            Messages.conversation_id == conversation_id,
        )
        .first()
    )
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    if cast(UUID, msg.sender_id) != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own messages",
        )

    setattr(msg, "content", data.content)
    setattr(msg, "is_edited", True)

    db.commit()
    db.refresh(msg)
    return msg


def delete_message(
    db: Session, current_user_id: UUID, conversation_id: UUID, message_id: UUID
) -> None:
    conv = _get_conversation_or_404(db, conversation_id)
    caller_part = _assert_participant(conv, current_user_id)

    msg = (
        db.query(Messages)
        .filter(
            Messages.id == message_id,
            Messages.conversation_id == conversation_id,
        )
        .first()
    )
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    is_sender = cast(UUID, msg.sender_id) == current_user_id
    is_admin = cast(ConversationRoleModel, caller_part.role) == ConversationRoleModel.admin

    if not (is_sender or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot delete this message",
        )

    db.delete(msg)
    db.commit()


# ---- Trainer / Trainee info ----

def get_connected_trainers(db: Session, current_user: User) -> List[Trainer_info]:
    try:
        connected_trainers = (
            db.query(Connections)
            .filter(
                or_(
                    Connections.addressee_id == current_user.id,
                    Connections.requester_id == current_user.id,
                ),
                Connections.connection_type == ConnectionType.trainership,
                Connections.status == ConnectionStatusModel.accepted,
            )
            .all()
        )

        connected_trainers_info: List[Trainer_info] = []

        for trainer in connected_trainers:
            trainer_id = (
                trainer.requester_id
                if trainer.addressee_id == current_user.id
                else trainer.addressee_id
            )  # type: ignore
            trainer_info = (
                db.query(Trainer_info).filter(Trainer_info.user_id == trainer_id).first()
            )
            if trainer_info:
                connected_trainers_info.append(trainer_info)

        return connected_trainers_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"something went wrong in the get-connected-trainers endpoint: {e}",
        )


def get_connected_trainees(db: Session, current_user: User) -> List[Dict[str, Any]]:
    try:
        logger.info("get_connected_trainees: current_user_id=%s", current_user.id)
        connected_trainees = (
            db.query(Connections)
            .filter(
                or_(
                    Connections.addressee_id == current_user.id,
                    Connections.requester_id == current_user.id,
                ),
                Connections.connection_type.in_(
                    [ConnectionType.trainership, "trainership"]
                ),
            )
            .all()
        )
        logger.info(
            "get_connected_trainees: connections_found=%s", len(connected_trainees)
        )

        connected_trainees_info: List[Dict[str, Any]] = []

        for connection in connected_trainees:
            trainee_id = (
                connection.requester_id
                if connection.addressee_id == current_user.id
                else connection.addressee_id
            )  # type: ignore
            logger.info(
                "get_connected_trainees: connection_id=%s requester_id=%s addressee_id=%s trainee_id=%s",
                connection.id,
                connection.requester_id,
                connection.addressee_id,
                trainee_id,
            )
            trainee_profile = (
                db.query(User_Profile).filter(User_Profile.user_id == trainee_id).first()
            )
            logger.info(
                "get_connected_trainees: trainee_profile_found=%s for trainee_id=%s",
                bool(trainee_profile),
                trainee_id,
            )
            if trainee_profile:
                trainee_user = db.query(User).filter(User.id == trainee_id).first()
                connected_trainees_info.append(
                    {
                        "id": trainee_profile.id,
                        "user_id": trainee_profile.user_id,
                        "email": trainee_user.email if trainee_user else None,
                        "address": trainee_profile.address,
                        "phone_number": trainee_profile.phone_number,
                        "bio": trainee_profile.bio,
                        "calorie_goal_daily": trainee_profile.calorie_goal_daily,
                        "sleep_quality": trainee_profile.sleep_quality,
                        "weight": trainee_profile.weight,
                        "height": trainee_profile.height,
                        "avatar_url": trainee_profile.avatar_url,
                    }
                )

        logger.info(
            "get_connected_trainees: returning_profiles=%s",
            len(connected_trainees_info),
        )

        return connected_trainees_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"something went wrong in the get-connected-trainees endpoint: {e}",
        )


def get_trainer_info(db: Session, user_id: UUID) -> Trainer_info:
    trainer_info = (
        db.query(Trainer_info).filter(Trainer_info.user_id == user_id).first()
    )
    if not trainer_info:
        logger.warning("Trainer info not found for user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trainer info not found"
        )

    return trainer_info


def get_my_conversations_items(db: Session, current_user: User) -> List[Dict[str, Any]]:
    try:
        logger.info("get_my_conversations: current_user_id=%s", current_user.id)
        conversations = (
            db.query(Conversations)
            .join(
                Conversation_Participants,
                Conversation_Participants.conversation_id == Conversations.id,
            )
            .filter(
                Conversation_Participants.user_id == current_user.id,
                Conversation_Participants.is_active == True,
                Conversations.type == ConversationTypeModel.direct,
            )
            .options(joinedload(Conversations.participants))
            .order_by(Conversations.last_message_at.desc().nullslast())
            .all()
        )

        logger.info(
            "get_my_conversations: conversations_found=%s", len(conversations)
        )

        participants_info: List[Dict[str, Any]] = []
        seen_user_ids = set()

        for conv in conversations:
            other_participant = next(
                (
                    participant
                    for participant in conv.participants
                    if participant.is_active
                    and participant.user_id != current_user.id
                ),
                None,
            )
            if not other_participant:
                logger.warning(
                    "get_my_conversations: no_other_participant for conversation_id=%s",
                    conv.id,
                )
                continue

            other_user_id = other_participant.user_id
            if other_user_id in seen_user_ids:
                continue
            seen_user_ids.add(other_user_id)

            logger.info(
                "get_my_conversations: conversation_id=%s other_user_id=%s",
                conv.id,
                other_user_id,
            )

            other_user = db.query(User).filter(User.id == other_user_id).first()
            if not other_user:
                logger.warning(
                    "get_my_conversations: other_user_not_found for other_user_id=%s",
                    other_user_id,
                )
                continue

            other_profile = (
                db.query(User_Profile)
                .filter(User_Profile.user_id == other_user_id)
                .first()
            )
            logger.info(
                "get_my_conversations: other_profile_found=%s for other_user_id=%s",
                bool(other_profile),
                other_user_id,
            )

            name = other_user.full_name or other_user.email
            participants_info.append(
                {
                    "id": other_profile.id if other_profile else None,
                    "user_id": other_user.id,
                    "name": name,
                    "address": other_profile.address if other_profile else None,
                    "phone_number": other_profile.phone_number if other_profile else None,
                    "bio": other_profile.bio if other_profile else None,
                    "calorie_goal_daily": other_profile.calorie_goal_daily if other_profile else None,
                    "sleep_quality": other_profile.sleep_quality if other_profile else None,
                    "weight": other_profile.weight if other_profile else None,
                    "height": other_profile.height if other_profile else None,
                    "avatar_url": other_profile.avatar_url if other_profile else None,
                }
            )

        logger.info(
            "get_my_conversations: returning_profiles=%s",
            len(participants_info),
        )

        return participants_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"something went wrong in the get-my-conversations endpoint: {e}",
        )


def list_trainers_limited(
    db: Session, current_user: User, skip: int, limit: int
) -> List[Trainer_info]:
    return (
        db.query(Trainer_info)
        .filter(Trainer_info.user_id != current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
