"""
SATH Platform API
=================
API Gateway para la plataforma multi-tenant de trading.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.database import init_db, close_db
from routers import auth, users, bots, keys, billing

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y cierre de la aplicación."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()

app = FastAPI(
    title="SATH Platform API",
    description="API para gestión de bots de trading multi-tenant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(keys.router, prefix="/api/v1/keys", tags=["keys"])
app.include_router(bots.router, prefix="/api/v1/bot", tags=["bot"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "SATH Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
