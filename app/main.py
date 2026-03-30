from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_NAME
from app.modules.event_detection.router import router as event_router
from app.modules.image_geo.router import router as image_router
from app.modules.digital_profile.router import router as digital_profile_router
from app.modules.infrastructure_intel.router import router as infrastructure_intel_router

app = FastAPI(title=APP_NAME)

app.include_router(infrastructure_intel_router, prefix="/api")
app.include_router(event_router, prefix="/api")
app.include_router(image_router, prefix="/api")
app.include_router(digital_profile_router, prefix="/api")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

NAV_ITEMS = [
    {"id": "dashboard", "label": "Панель управления", "href": "/"},
    {"id": "event-detection", "label": "Выявление событий", "href": "/modules/event-detection"},
    {"id": "image-geo", "label": "Анализ изображений и геолокации", "href": "/modules/image-geo"},
    {"id": "digital-profile", "label": "Username / Email Intelligence", "href": "/modules/digital-profile"},
    {"id": "graph-engine", "label": "Graph Engine", "href": "#", "disabled": True},
    {"id": "geo-intelligence", "label": "Geo Intelligence", "href": "#", "disabled": True},
    {"id": "alerts", "label": "Раннее предупреждение", "href": "#", "disabled": True},
    {"id": "infra", "label": "Infrastructure Intelligence", "href": "/modules/infrastructure-intel"},
]

COMMON = {"nav_items": NAV_ITEMS}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "Оперативная панель",
            "active_nav": "dashboard",
            **COMMON
        }
    )


@app.get("/modules/event-detection", response_class=HTMLResponse)
async def event_detection_page(request: Request):
    return templates.TemplateResponse(
        "event_detection.html",
        {
            "request": request,
            "title": "Выявление событий",
            "active_nav": "event-detection",
            **COMMON
        }
    )


@app.get("/modules/image-geo", response_class=HTMLResponse)
async def image_geo_page(request: Request):
    return templates.TemplateResponse(
        "image_geo.html",
        {
            "request": request,
            "title": "Анализ изображений и геолокации",
            "active_nav": "image-geo",
            **COMMON
        }
    )


@app.get("/modules/digital-profile", response_class=HTMLResponse)
async def digital_profile_page(request: Request):
    return templates.TemplateResponse(
        "digital_profile.html",
        {
            "request": request,
            "title": "Username / Email Intelligence",
            "active_nav": "digital-profile",
            **COMMON
        }
    )


@app.get("/modules/infrastructure-intel", response_class=HTMLResponse)
async def infrastructure_intel_page(request: Request):
    return templates.TemplateResponse(
        "infrastructure_intel.html",
        {
            "request": request,
            "title": "Infrastructure Intelligence",
            "active_nav": "infra",
            **COMMON
        }
    )