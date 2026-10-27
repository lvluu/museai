from fastapi import APIRouter

from . import admin, chat, dashboard, health, images, media, models, posting, responses, videos


def build_router() -> APIRouter:
    router = APIRouter()
    for module in (health, models, chat, responses, images, videos, media, admin, dashboard, posting):
        router.include_router(module.router)
    return router
