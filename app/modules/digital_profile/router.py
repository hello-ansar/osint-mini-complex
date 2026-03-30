from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from .service import analyze_profile

router = APIRouter()


class DigitalProfileRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    category: Optional[str] = None
    module: Optional[str] = None
    proxy_file: Optional[str] = None
    validate_proxies: bool = False


@router.post("/digital-profile/analyze")
async def digital_profile_analyze(payload: DigitalProfileRequest):
    return analyze_profile(
        email=payload.email,
        username=payload.username,
        category=payload.category,
        module=payload.module,
        proxy_file=payload.proxy_file,
        validate_proxies=payload.validate_proxies,
    )