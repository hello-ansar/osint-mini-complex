from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from .service import analyze_infrastructure

router = APIRouter()


class InfraIntelRequest(BaseModel):
    domain: str
    tool_path: Optional[str] = None


@router.post("/infrastructure-intel/analyze")
async def infrastructure_intel_analyze(payload: InfraIntelRequest):
    return analyze_infrastructure(
        domain=payload.domain,
        tool_path=payload.tool_path,
    )