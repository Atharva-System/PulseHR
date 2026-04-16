"""HR AI Platform — FastAPI entry point."""

import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.auth import hash_password
from app.config import settings
from app.middleware import add_middleware
from api.routes.chat import router as chat_router
from api.routes.auth import router as auth_router
from api.routes.users import router as users_router
from api.routes.admin import router as admin_router
from api.routes.conversations import router as conversations_router
from api.routes.reports import router as reports_router
from api.routes.notifications import router as notifications_router
from api.routes.agents import router as agents_router
from api.routes.my import router as my_router
from api.routes.feedback import router as feedback_router
from api.routes.policies import router as policies_router
from api.routes.messages import router as messages_router
from db.connection import get_engine, get_db_session
from db.models import Base, UserModel
from escalation.sla_checker import sla_checker_loop
from utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        if settings.database_url:
            engine = get_engine()
            Base.metadata.create_all(engine)
            logger.info("Database tables verified / created")

            # Auto-migrate: add new columns to existing tables
            with engine.connect() as conn:
                try:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                        "receive_notifications BOOLEAN DEFAULT FALSE"
                    ))
                    conn.commit()
                except Exception as e:
                    logger.warning("Column migration skipped: %s", e)

            session = get_db_session()
            try:
                existing_admin = session.query(UserModel).filter_by(
                    role=settings.admin_role,
                    is_active=True,
                ).first()

                if existing_admin is None and settings.admin_password:
                    duplicate_user = session.query(UserModel).filter(
                        (UserModel.username == settings.admin_username) |
                        (UserModel.email == settings.admin_email)
                    ).first()

                    if duplicate_user is None:
                        new_admin = UserModel(
                            id=str(uuid.uuid4()),
                            username=settings.admin_username,
                            email=settings.admin_email,
                            full_name=settings.admin_full_name,
                            password_hash=hash_password(settings.admin_password),
                            role=settings.admin_role,
                            is_active=True,
                        )
                        session.add(new_admin)
                        session.commit()
                        logger.info(
                            "Initial admin account created: %s",
                            settings.admin_username,
                        )
                    else:
                        logger.warning(
                            "Admin seed skipped because a user already exists with username/email: %s",
                            duplicate_user.username,
                        )
            finally:
                session.close()

        logger.info(
            f"{settings.app_name} v{settings.app_version} starting — "
            f"model={settings.model_name}"
        )

        # Launch SLA checker background task
        sla_task = asyncio.create_task(sla_checker_loop())
        yield
        # Shutdown
        sla_task.cancel()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-agent HR AI platform powered by LangGraph",
        lifespan=lifespan,
    )

    # Middleware
    add_middleware(app)

    # Routes
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(admin_router)
    app.include_router(conversations_router)
    app.include_router(reports_router)
    app.include_router(notifications_router)
    app.include_router(agents_router)
    app.include_router(my_router)
    app.include_router(feedback_router)
    app.include_router(policies_router)
    app.include_router(messages_router)
    app.include_router(chat_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()
