"""SigAid Authority Service - FastAPI Application."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings, ConfigurationError
from .routers import router
from .middleware import RateLimitMiddleware, RateLimiter
from .logging import setup_logging, get_logger

# Configure logging
setup_logging(debug=settings.DEBUG, json_format=not settings.DEBUG)
logger = get_logger("main")

app = FastAPI(
    title="SigAid Authority Service",
    description="Cryptographic agent identity protocol with exclusive leasing and state continuity",
    version="0.1.0",
)

# Rate limiting (uses Redis if REDIS_URL is configured)
rate_limiter = RateLimiter(redis_url=settings.REDIS_URL)
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

# CORS - Use configured origins or restrict in production
cors_origins = settings.cors_origins_list
if not cors_origins:
    if settings.DEBUG or settings.ALLOW_INSECURE_DEFAULTS:
        # Allow all origins in development
        cors_origins = ["*"]
        logger.warning(
            "CORS allowing all origins (DEBUG mode). "
            "Set CORS_ORIGINS for production."
        )
    else:
        # Default to no CORS in production if not configured
        cors_origins = []
        logger.info(
            "CORS disabled (no origins configured). "
            "Set CORS_ORIGINS to enable cross-origin requests."
        )

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    )

# Include API router
app.include_router(router, prefix=settings.API_PREFIX)


@app.on_event("startup")
async def startup_event():
    """Log startup information and security configuration."""
    # Log security configuration
    security_config = {
        "cors_origins": len(cors_origins) if cors_origins != ["*"] else "all",
        "rate_limiting": "redis" if settings.REDIS_URL else "in-memory",
        "debug_mode": settings.DEBUG,
    }

    logger.info(
        "SigAid Authority Service starting",
        extra={
            "version": "0.1.0",
            "debug": settings.DEBUG,
            "database": f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}",
            "security": security_config,
        }
    )

    # Security warnings for production
    if not settings.DEBUG and not settings.ALLOW_INSECURE_DEFAULTS:
        if cors_origins == ["*"]:
            logger.warning("SECURITY: CORS allows all origins in production")
        if not settings.REDIS_URL:
            logger.warning("SECURITY: Using in-memory rate limiting (not suitable for multi-instance)")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown."""
    logger.info("SigAid Authority Service shutting down")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "sigaid-authority"}


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "SigAid Authority Service",
        "version": "0.1.0",
        "docs": "/docs",
    }
