"""Health-check route."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return a simple health status."""
    return {"status": "ok"}
