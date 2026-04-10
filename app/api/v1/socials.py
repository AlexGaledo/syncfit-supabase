from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models import social
import datetime
#=============================ENDPOINTS==================================
socials_router = APIRouter(prefix="/socials", tags=["Socials"])

@socials_router.get("/create_conversation")
async def create_conversation():
    """
    Create a new conversation between users
    """
    return {"message": "Create conversation endpoint - To be implemented"}


async def send_message():
    """
    Send a message in a conversation
    """
    return {"message": "Send message endpoint - To be implemented"}


#=============================QUERY==================================


def get_conversation_messages(db:Session, conversation_id:str, date:datetime.datetime, limit:int = 20, skip:int = 0 ):
    return (
        db.query(social.Messages)
        .filter(social.Messages.conversation_id == conversation_id)
        .filter(social.Messages.created_at > date)
        .limit(limit)
        .offset(skip)
        .all()
    )


def get_conversation_participants(db:Session, conversation_id:str):
    return (
        
    )