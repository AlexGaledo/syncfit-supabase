"""
Social schemas for request/response validation
"""
from pydantic import BaseModel, ConfigDict, Field
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
    name: Optional[str] = Field(None, max_length=100)  # for group conversations


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation"""
    creator_id: UUID
    participant_ids: list[UUID] = Field(min_length=1)


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation (rename group, etc.)"""
    name: Optional[str] = Field(None, max_length=100)


class ConversationResponse(ConversationBase):
    """Schema for conversation response"""
    id: UUID
    creator_id: UUID
    created_at: datetime
    last_message_at: Optional[datetime] = None
    participants: list["ConversationParticipantResponse"] = []  # embedded participants
    last_message: Optional["MessageResponse"] = None            # embedded last message preview

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


class ConversationParticipantUpdate(BaseModel):
    """Schema for updating a participant role"""
    role: ConversationRole


class ConversationParticipantResponse(ConversationParticipantBase):
    """Schema for conversation participant response"""
    joined_at: datetime
    is_active: bool = True  # False if they left the conversation

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# MESSAGES SCHEMAS
# ============================================================================

class MessageBase(BaseModel):
    """Base message schema"""
    content: str = Field(min_length=1, max_length=5000)
    type: MessageType = MessageType.text


class MessageCreate(MessageBase):
    """Schema for creating a message"""
    conversation_id: UUID
    sender_id: UUID
    reply_to_id: Optional[UUID] = None  # for replying to a specific message


class MessageUpdate(BaseModel):
    """Schema for editing a message"""
    content: str = Field(min_length=1, max_length=5000)


class MessageResponse(MessageBase):
    """Schema for message response"""
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    reply_to_id: Optional[UUID] = None
    is_edited: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PAGINATED RESPONSES
# ============================================================================

class PaginatedMessages(BaseModel):
    """Paginated message list for chat history"""
    messages: list[MessageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class PaginatedConversations(BaseModel):
    """Paginated conversation list"""
    conversations: list[ConversationResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Resolve forward references
ConversationResponse.model_rebuild()