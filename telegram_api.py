"""
FastAPI HTTP bridge for Telegram functionality.
Exposes the existing Telethon client via REST API for the TypeScript agent.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.client import client
from backend.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Telegram client lifecycle."""
    # Client is already initialized in backend.client, just start it
    await client.start()
    print("✅ Telegram client connected")
    
    yield
    
    await client.disconnect()
    print("👋 Telegram client disconnected")


app = FastAPI(
    title="Telegram API Bridge",
    description="HTTP API for Telegram operations",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
