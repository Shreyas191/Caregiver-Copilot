"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import chat, health, me, care_recipients, medications

app = FastAPI(
    title="Caregiver Co-Pilot API",
    description="Backend API for the Caregiver Co-Pilot application",
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router)
app.include_router(me.router)
app.include_router(care_recipients.router, prefix="/api/v1")
app.include_router(medications.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
