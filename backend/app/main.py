from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, health, users
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered doctor recommendation & appointment booking platform API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include v1 API router (/api/v1/...)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Also expose direct convenience top-level routes (/health, /me, /auth)
app.include_router(health.router)
app.include_router(users.router)
app.include_router(auth.router)


@app.get("/", summary="Root index")
def root_index():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "health_check": "/health",
        "docs": "/docs",
    }
