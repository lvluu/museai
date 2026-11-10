from fastapi import APIRouter

from . import (
    admin,
    autopost,
    campaign,
    chat,
    dashboard,
    hands,
    health,
    images,
    media,
    models,
    posting,
    profiles,
    projects,
    responses,
    videos,
)


def build_router() -> APIRouter:
    router = APIRouter()
    for module in (health, models, chat, responses, images, videos, projects, media, admin, dashboard, posting, autopost, hands, campaign, profiles):
        router.include_router(module.router)
    router.include_router(autopost.callback_router)
    return router
