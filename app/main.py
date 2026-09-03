import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import routers as v1_routers
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
)

app.include_router(v1_routers)

# CORS origins ro'yxatini to'g'irlash
cors_list = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Media papkalarni yaratish va mount qilish
os.makedirs("media/uploads", exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")