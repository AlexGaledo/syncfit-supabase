"""
Example Items routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.models.item import Item
from app.schemas.item import ItemResponse, ItemCreate, ItemUpdate

router = APIRouter(prefix="/items", tags=["Items"])


@router.get("/", response_model=List[ItemResponse])
async def get_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all items for the current user
    """
    # Get items owned by current user
    user_id = current_user.get("sub")
    items = db.query(Item).filter(Item.owner_id == user_id).offset(skip).limit(limit).all()
    return items


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific item by ID
    """
    user_id = current_user.get("sub")
    item = db.query(Item).filter(
        Item.id == item_id,
        Item.owner_id == user_id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    return item


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new item
    """
    user_id = current_user.get("sub")
    
    # Create new item
    db_item = Item(
        **item_data.model_dump(),
        owner_id=user_id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: UUID,
    item_data: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an item
    """
    user_id = current_user.get("sub")
    item = db.query(Item).filter(
        Item.id == item_id,
        Item.owner_id == user_id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Update item fields
    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an item
    """
    user_id = current_user.get("sub")
    item = db.query(Item).filter(
        Item.id == item_id,
        Item.owner_id == user_id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    db.delete(item)
    db.commit()
    return None
