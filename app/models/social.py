"""
Social database models - Connections, Conversations, Messages
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from app.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class ConnectionStatus(enum.Enum):
    """Enum for connection request status"""
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    blocked = "blocked"


class ConversationType(enum.Enum):
    """Enum for conversation type"""
    direct = "direct"
    group = "group"


class ConversationRole(enum.Enum):
    """Enum for participant role in a conversation"""
    member = "member"
    admin = "admin"


class MessageType(enum.Enum):
    """Enum for message content type"""
    text = "text"
    image = "image"
    file = "file"


# ============================================================================
# SOCIAL MODELS
# ============================================================================

class Connections(Base):
    """
    Connections model - Friend/connection requests between users
    """
    __tablename__ = "connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # type: ignore
    addressee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # type: ignore
    status = Column(Enum(ConnectionStatus), default=ConnectionStatus.pending, nullable=False)  # type: ignore

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    requester = relationship("User", foreign_keys=[requester_id], backref="sent_connections")
    addressee = relationship("User", foreign_keys=[addressee_id], backref="received_connections")

    def __repr__(self):
        return f"<Connection {self.requester_id} -> {self.addressee_id} ({self.status})>"


class Conversations(Base):
    """
    Conversations model - Direct or group conversations
    """
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    type = Column(Enum(ConversationType), default=ConversationType.direct, nullable=False)  # type: ignore

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    participants = relationship("Conversation_Participants", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Messages", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation {self.id} ({self.type})>"


class Conversation_Participants(Base):
    """
    Conversation Participants model - Links users to conversations
    """
    __tablename__ = "conversation_participants"

    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True)  # type: ignore
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)  # type: ignore
    role = Column(Enum(ConversationRole), default=ConversationRole.member, nullable=False)  # type: ignore
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("Conversations", back_populates="participants")
    user = relationship("User", backref="conversation_participations")

    def __repr__(self):
        return f"<Participant user={self.user_id} conv={self.conversation_id}>"


class Messages(Base):
    """
    Messages model - Individual messages in a conversation
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)  # type: ignore
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # type: ignore
    content = Column(Text, nullable=False)
    type = Column(Enum(MessageType), default=MessageType.text, nullable=False)  # type: ignore

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("Conversations", back_populates="messages")
    sender = relationship("User", backref="sent_messages")

    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id}>"
