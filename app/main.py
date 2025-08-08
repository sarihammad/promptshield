"""
Main FastAPI application for the LLM Gateway API.

This module serves as the entry point for the FastAPI application,
setting up middleware, routers, and configuration.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.endpoints import router as v1_router

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_type": type(exc).__name__,
            "request_id": request_id,
            "detail": str(exc) if settings.log_level == "DEBUG" else "An unexpected error occurred"
        }
    )


# Include routers
app.include_router(v1_router, prefix="/v1", tags=["v1"])


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "LLM Gateway API",
        "version": settings.api_version,
        "description": settings.api_description,
        "docs": "/docs",
        "health": "/v1/health"
    }


@app.get("/health", tags=["health"])
async def root_health():
    """Root health check endpoint."""
    return {"status": "healthy", "service": "llm-gateway"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    ) 