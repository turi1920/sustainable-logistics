import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.core.exceptions import (
    DomainException,
    InvalidStateTransitionError,
    ResourceNotFoundError,
    SanitizationGateError,
    UnauthorizedActionError,
)
from backend.app.core.logging import logger
from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.jobs.timeout_worker import TimeoutWorker
from backend.app.schemas.common import HealthResponse

stop_worker_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist
    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized.")

    # Start background SLA worker task
    worker_task = asyncio.create_task(TimeoutWorker.run_periodic_worker(stop_worker_event))
    
    yield

    # Shutdown
    logger.info("Stopping background SLA worker...")
    stop_worker_event.set()
    try:
        await asyncio.wait_for(worker_task, timeout=5.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass
    await engine.dispose()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Enterprise API for Post-Consumer Sustainable Reverse Logistics, NRV Economics, and Device Sanitization Gates.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(SanitizationGateError)
async def sanitization_gate_exception_handler(request: Request, exc: SanitizationGateError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": exc.code, "message": exc.message, "details": exc.details}
    )


@app.exception_handler(InvalidStateTransitionError)
async def state_transition_exception_handler(request: Request, exc: InvalidStateTransitionError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": exc.code, "message": exc.message, "details": exc.details}
    )


@app.exception_handler(UnauthorizedActionError)
async def unauthorized_action_exception_handler(request: Request, exc: UnauthorizedActionError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"error": exc.code, "message": exc.message, "details": exc.details}
    )


@app.exception_handler(ResourceNotFoundError)
async def not_found_exception_handler(request: Request, exc: ResourceNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": exc.code, "message": exc.message, "details": exc.details}
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": exc.code, "message": exc.message, "details": exc.details}
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version="1.0.0",
        database="connected"
    )


app.include_router(api_router, prefix=settings.API_V1_STR)
