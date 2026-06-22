from contextlib import asynccontextmanager
import logging
import os
import sys
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config.settings import settings
from app.core.database.postgres import engine
from app.core.database.redis import init_redis
from app.core.database.mongodb import check_mongo_connection
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware

# Import Routers from the new layered architecture
from app.routes.auth import router as auth_router
from app.routes.superadmin import router as superadmin_router
from app.routes.companies import router as company_router
from app.routes.departments import router as department_router
from app.routes.employees import router as employee_router
from app.routes.documents import router as document_router
from app.routes.subscriptions import router as subscription_router
from app.routes.notifications import router as notification_router
from app.routes.chat import router as chat_router
from app.routes.websocket import router as websocket_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print("INFO:  Starting DVP Portal Backend...", file=sys.stderr)

    # 1. Initialize Redis connection gracefully (does not crash if offline)
    await init_redis()

    # 2. Check MongoDB connection gracefully
    mongo_ok = await check_mongo_connection()
    if mongo_ok:
        print("INFO:  MongoDB connected successfully.", file=sys.stderr)
    else:
        print("WARNING: MongoDB is not available.", file=sys.stderr)

    # 3. Create upload directory locally if using LocalStorageService
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    yield

    # Shutdown actions
    print("INFO:  Shutting down DVP Portal Backend...", file=sys.stderr)
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Multi-Tenant SaaS Digital Verification Portal (DVP) Backend API",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Mount static folder for uploads serving
app.mount("/static/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception in request {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(superadmin_router, prefix=settings.API_V1_STR)
app.include_router(company_router, prefix=settings.API_V1_STR)
app.include_router(employee_router, prefix=settings.API_V1_STR)
app.include_router(department_router, prefix=settings.API_V1_STR)
app.include_router(document_router, prefix=settings.API_V1_STR)
app.include_router(subscription_router, prefix=settings.API_V1_STR)
app.include_router(notification_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(websocket_router)


@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "api_docs": "/docs",
    }