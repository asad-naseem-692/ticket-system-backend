from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

from app.api.routers import auth, tickets

app = FastAPI(
    title="Customer Support Ticket & SLA Automation API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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

@app.get("/health", tags=["Health"])
def health_check():
    """Basic health check endpoint for Railway and monitoring."""
    return {"status": "healthy"}
