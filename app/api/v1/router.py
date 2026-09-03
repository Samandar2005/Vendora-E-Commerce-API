from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, stores, categories, products, cart, orders, payments

routers = APIRouter()
routers.include_router(auth.router)
routers.include_router(users.router)
routers.include_router(stores.router)
routers.include_router(categories.router)
routers.include_router(products.router)
routers.include_router(cart.router)
routers.include_router(orders.router)
routers.include_router(payments.router)