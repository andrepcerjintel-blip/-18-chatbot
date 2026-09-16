from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import characters, chat, conversations, health, media
from app.config import get_settings
from app.database.session import init_db
from app.logging_config import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("startup app_env=%s host=%s port=%s", settings.app_env, settings.host, settings.port)
    init_db()
    logger.info("database ready url=%s", settings.database_url)
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Adult Companion App (Local & Private)",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Privacidade: CORS restrito a origens locais configuradas via .env.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(characters.router)
    app.include_router(conversations.router)
    app.include_router(chat.router)
    app.include_router(media.router)

    return app


app = create_app()
