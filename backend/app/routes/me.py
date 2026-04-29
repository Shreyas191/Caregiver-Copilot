from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import get_current_user_id

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
async def get_me(user_id: Annotated[str, Depends(get_current_user_id)]) -> dict:
    """Return the currently authenticated user's ID."""
    return {"clerk_user_id": user_id}
