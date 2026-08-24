from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

from app.api.routers import auth, tickets, users, comments, attachments, notifications
from app.workers.sla_monitor_worker import start_sla_worker, stop_sla_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch background SLA monitor
    start_sla_worker(interval_seconds=60)
    yield
    # Shutdown: clean stop
    stop_sla_worker()

app = FastAPI(
    title="Customer Support Ticket & SLA Automation API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(users.router)
app.include_router(comments.router)
app.include_router(attachments.router)
app.include_router(notifications.router)

@app.get("/health", tags=["Health"])
def health_check():
    """Basic health check endpoint for Railway and monitoring."""
    return {"status": "healthy"}
