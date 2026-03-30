from fastapi import APIRouter
from .service import get_event_payload

router = APIRouter(tags=["Event Detection"])

@router.get("/event-detection")
async def event_detection():
    return get_event_payload()
