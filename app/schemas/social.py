"""
Social schemas for request/response validation
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ConnectionStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    blocked = "blocked"


class ConversationType(str, Enum):
    direct = "direct"
    group = "group"


class ConversationRole(str, Enum):
    member = "member"
    admin = "admin"


class MessageType(str, Enum):
    text = "text"
    image = "image"
    file = "file"


# ============================================================================
# CONNECTIONS SCHEMAS
# ============================================================================

class ConnectionBase(BaseModel):
    """Base connection schema"""
    requester_id: UUID
    addressee_id: UUID


class ConnectionCreate(ConnectionBase):
    """Schema for creating a connection request"""
    pass


class ConnectionUpdate(BaseModel):
    """Schema for updating a connection (accept/decline/block)"""
    status: ConnectionStatus


class ConnectionResponse(ConnectionBase):
    """Schema for connection response"""
    id: UUID
    status: ConnectionStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CONVERSATIONS SCHEMAS
# ============================================================================

class ConversationBase(BaseModel):
    """Base conversation schema"""
    type: ConversationType = ConversationType.direct


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation"""
    pass


class ConversationResponse(ConversationBase):
    """Schema for conversation response"""
    id: UUID
    created_at: datetime
    last_message_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CONVERSATION PARTICIPANTS SCHEMAS
# ============================================================================

class ConversationParticipantBase(BaseModel):
    """Base conversation participant schema"""
    conversation_id: UUID
    user_id: UUID
    role: ConversationRole = ConversationRole.member


class ConversationParticipantCreate(ConversationParticipantBase):
    """Schema for adding a participant to a conversation"""
    pass


class ConversationParticipantResponse(ConversationParticipantBase):
    """Schema for conversation participant response"""
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# MESSAGES SCHEMAS
# ============================================================================

class MessageBase(BaseModel):
    """Base message schema"""
    content: str
    type: MessageType = MessageType.text


class MessageCreate(MessageBase):
    """Schema for creating a message"""
    conversation_id: UUID
    sender_id: UUID


class MessageResponse(MessageBase):
    """Schema for message response"""
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
