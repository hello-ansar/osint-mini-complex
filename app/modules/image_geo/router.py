from fastapi import APIRouter, UploadFile, File
from .service import analyze_image_bytes

router = APIRouter(tags=["Image & Geo Intelligence"])

@router.post("/image-geo/analyze")
async def analyze_image(file: UploadFile = File(...)):
    return analyze_image_bytes(await file.read(), file.filename)
