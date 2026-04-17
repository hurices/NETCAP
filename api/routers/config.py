"""
Endpoints de lecture et modification de la configuration en temps réel.
Monté sur le préfixe /config dans api/main.py.

Tous les endpoints de modification nécessitent le token admin.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config
from api.schemas import ConfigSeuils, ParametresExport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["Configuration"])

# État mutable de la configuration — partagé avec main.py via import
# Initialisé avec les valeurs de config.py
_config_courante = ConfigSeuils(
    zscore_seuil=config.ANOMALIE_ZSCORE_SEUIL,
    volume_max_session_mb=config.ANOMALIE_VOLUME_MAX_SESSION_MB,
    duree_session_max_min=config.ANOMALIE_DUREE_SESSION_MAX_MIN,
    categories_bloquees=list(config.CATEGORIES_BLOQUEES),
    requetes_par_minute_max=config.ANOMALIE_REQUETES_PAR_MINUTE_MAX,
)


async def _verifier_token_admin(request: Request) -> str:
    """Dépendance : vérifie le token admin dans les headers."""
    token = request.headers.get(config.ADMIN_TOKEN_HEADER)
    if not token or token != config.ADMIN_TOKEN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token admin invalide. Header requis : {config.ADMIN_TOKEN_HEADER}",
        )
    return token


def get_config_courante() -> ConfigSeuils:
    """Retourne la configuration actuellement active. Utilisable comme dépendance."""
    return _config_courante


@router.get(
    "/seuils",
    response_model=ConfigSeuils,
    summary="Lire la configuration courante",
    description="Retourne les seuils d'alerte et paramètres actuellement actifs.",
)
async def lire_seuils() -> ConfigSeuils:
    """Retourne la configuration en mémoire, initialisée depuis config.py."""
    return _config_courante


@router.post(
    "/seuils",
    response_model=ConfigSeuils,
    summary="Mettre à jour les seuils d'alerte",
)
async def mettre_a_jour_seuils(nouveaux_seuils: ConfigSeuils) -> ConfigSeuils:
    """
    Met à jour la configuration en mémoire.
    """
    global _config_courante
    _config_courante = nouveaux_seuils
    
    # Mettre à jour les composants en temps réel
    from analyse.pipeline import pipeline
    pipeline.detecteur.zscore_threshold = nouveaux_seuils.zscore_seuil
    pipeline.detecteur.max_volume_mb = nouveaux_seuils.volume_max_session_mb
    
    logger.info("Seuils mis à jour avec succès.")
    return _config_courante


@router.get(
    "/export/csv",
    summary="Exporter les données en CSV",
)
async def export_csv(
    debut: datetime | None = None,
    fin: datetime | None = None,
) -> StreamingResponse:
    """
    Génération du CSV depuis le DataFrame Pandas.
    """
    from analyse.pipeline import pipeline
    import io
    
    df = pipeline.dataframe
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="Aucune donnée à exporter.")
    
    # Filtrage temporel si demandé
    if debut:
        df = df[df['timestamp'] >= debut]
    if fin:
        df = df[df['timestamp'] <= fin]
        
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=export_netcapt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )