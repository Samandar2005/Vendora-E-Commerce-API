from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1.router import routers as v1_routers

app = FastAPI(
    title=get_settings().title,
    description=get_settings().description,
    version=get_settings().version,
)

app.include_router(v1_routers)

# Katta harflar bilan CORS_ORIGINS
cors_list = get_settings().CORS_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)