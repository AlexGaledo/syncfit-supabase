"""
Social database models - Connections, Conversations, Messages
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum, UniqueConstraint
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
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    blocked = "blocked"


class ConversationType(enum.Enum):
    direct = "direct"
    group = "group"


class ConversationRole(enum.Enum):
    member = "member"
    admin = "admin"


class MessageType(enum.Enum):
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
    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name="uq_connections_pair"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
    addressee_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
    status = Column(Enum(ConnectionStatus), default=ConnectionStatus.pending, nullable=False)

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(Enum(ConversationType), default=ConversationType.direct, nullable=False)
    name = Column(String(100), nullable=True)                                             # added — group chat name
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'), nullable=False)      # added — tracks who created it

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    last_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete='CASCADE'), nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[creator_id], backref="created_conversations")
    participants = relationship("Conversation_Participants", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship(
        "Messages",
        back_populates="conversation",
        cascade="all, delete-orphan",
        foreign_keys="[Messages.conversation_id]"
    )
    last_message = relationship("Messages", foreign_keys=[last_message_id])

    def __repr__(self):
        return f"<Conversation {self.id} ({self.type})>"


class Conversation_Participants(Base):
    """
    Conversation Participants model - Links users to conversations
    """
    __tablename__ = "conversation_participants"

    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'), primary_key=True)
    role = Column(Enum(ConversationRole), default=ConversationRole.member, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)                             # added — tracks if user left

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(Enum(MessageType), default=MessageType.text, nullable=False)
    reply_to_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete='CASCADE'), nullable=True)   # added — reply threading
    is_edited = Column(Boolean, default=False, nullable=False)                            # added — edit tracking

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)      # added — edit timestamp

    # Relationships
    conversation = relationship("Conversations", back_populates="messages", foreign_keys=[conversation_id])
    sender = relationship("User", backref="sent_messages")
    reply_to = relationship("Messages", remote_side="Messages.id", foreign_keys=[reply_to_id])  # added — self-referential

    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id}>"