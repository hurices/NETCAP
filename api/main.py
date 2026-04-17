from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NetCaptAPI")

from api.routers import sessions, analytics, config

# Initialisation de l'application
app = FastAPI(
    title="NetCapt API",
    description="API d'administration du système NetCapt - Sprints 4 & 5",
    version="1.1.0"
)

# Inclusion des routers
app.include_router(sessions.router)
app.include_router(analytics.router)
app.include_router(config.router)
from analyse.pipeline import pipeline

@app.on_event("startup")
def startup_event():
    logger.info("Démarrage du pipeline d'analyse...")
    pipeline.start()

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Arrêt du pipeline d'analyse...")
    pipeline.stop()


@app.get("/", tags=["Système"])
def root():
    """
    Endpoint de bienvenue.
    """
    return {
        "message": "NetCapt API is running",
        "documentation": "/docs",
        "version": "1.1.0"
    }


@app.get("/health", tags=["Système"])
def health():
    """
    Vérification de l'état de santé du système.
    """
    from shared.state import get_stats
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "stats": get_stats()
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Une erreur interne est survenue."},
    )