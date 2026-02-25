from fastapi import APIRouter, Depends


socials_router = APIRouter(prefix="/socials", tags=["Socials"])

@socials_router.get("/create_conversation")
async def create_conversation():
    """
    Create a new conversation between users
    """
    return {"message": "Create conversation endpoint - To be implemented"}