"""Unit tests for socials endpoints (connections, conversations, messages)."""
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from conftest import USER_ID
from app.models.social import ConnectionStatus as ConnectionStatusModel


def _fake_connection(requester_id=None, addressee_id=None):
    return SimpleNamespace(
        id=uuid4(),
        requester_id=requester_id or USER_ID,
        addressee_id=addressee_id or uuid4(),
        status=ConnectionStatusModel.pending,
        created_at=datetime(2024, 1, 1),
        updated_at=None,
    )


def _fake_conversation(user_id=None):
    uid = user_id or USER_ID
    participant = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        user_id=uid,
        role=__import__("app.models.social", fromlist=["ConversationRole"]).ConversationRole.admin,
        is_active=True,
        joined_at=datetime(2024, 1, 1),
    )
    conv = SimpleNamespace(
        id=uuid4(),
        type=__import__("app.models.social", fromlist=["ConversationType"]).ConversationType.direct,
        name=None,
        creator_id=uid,
        last_message_at=None,
        last_message_id=None,
        created_at=datetime(2024, 1, 1),
        updated_at=None,
        participants=[participant],
        last_message=None,
    )
    participant.conversation_id = conv.id
    return conv


# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------

def test_get_connections_empty(client, mock_db):
    mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    response = client.get("/api/v1/socials/connections")
    assert response.status_code == 200
    assert response.json() == []


def test_send_connection_to_self(client, mock_db):
    # Sending a connection request to yourself → 400
    response = client.post(f"/api/v1/socials/connections?addressee_id={USER_ID}")
    assert response.status_code == 400


def test_send_connection_user_not_found(client, mock_db):
    other_id = uuid4()
    # Addressee user not found in DB
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.post(f"/api/v1/socials/connections?addressee_id={other_id}")
    assert response.status_code == 404


def test_remove_connection_not_found(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.delete(f"/api/v1/socials/connections/{uuid4()}")
    assert response.status_code == 404


def test_respond_to_connection_not_found(client, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.patch(
        f"/api/v1/socials/connections/{uuid4()}?new_status=accepted"
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

def test_get_conversation_not_found(client, mock_db):
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None
    response = client.get(f"/api/v1/socials/conversations/{uuid4()}")
    assert response.status_code == 404


def test_create_direct_conversation_requires_exactly_two(client, mock_db):
    # Direct conversation with 3 participants (creator + 2 others) → 400
    from conftest import USER_ID
    other1, other2 = uuid4(), uuid4()

    mock_db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=other1)
    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []

    payload = {
        "type": "direct",
        "creator_id": str(USER_ID),
        "participant_ids": [str(other1), str(other2)],
    }
    response = client.post("/api/v1/socials/conversations", json=payload)
    assert response.status_code == 400


def test_create_group_conversation_requires_name(client, mock_db):
    from conftest import USER_ID
    other_id = uuid4()
    mock_db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=other_id)
    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []

    payload = {
        "type": "group",
        "creator_id": str(USER_ID),
        "participant_ids": [str(other_id)],
        # name intentionally omitted → 400
    }
    response = client.post("/api/v1/socials/conversations", json=payload)
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def test_send_message_to_nonexistent_conversation(client, mock_db):
    # MessageCreate requires conversation_id and sender_id in body (schema design)
    from conftest import USER_ID
    conv_id = uuid4()
    payload = {
        "content": "Hello",
        "type": "text",
        "conversation_id": str(conv_id),
        "sender_id": str(USER_ID),
    }
    response = client.post(f"/api/v1/socials/conversations/{conv_id}/messages", json=payload)
    assert response.status_code == 404


def test_get_messages_conversation_not_found(client, mock_db):
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None
    response = client.get(f"/api/v1/socials/conversations/{uuid4()}/messages")
    assert response.status_code == 404
