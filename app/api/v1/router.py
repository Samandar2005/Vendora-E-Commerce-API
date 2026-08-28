from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, stores

routers = APIRouter()
routers.include_router(auth.router)
routers.include_router(users.router)
routers.include_router(stores.router)