"""
Regroupe tous les endpoints liés aux sessions utilisateurs.
Monté sur le préfixe /sessions dans api/main.py.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config
from api.schemas import SessionActive, SessionDetail
from shared.state import lister_sessions_actives, revoquer_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


async def _verifier_token_admin(request: Request) -> str:
    """Vérifie le token admin dans les headers. Lève HTTP 401 si invalide."""
    token = request.headers.get(config.ADMIN_TOKEN_HEADER)
    if not token or token != config.ADMIN_TOKEN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token admin invalide. Header requis : {config.ADMIN_TOKEN_HEADER}",
        )
    return token


@router.get(
    "",
    response_model=list[SessionActive],
    summary="Lister les sessions actives",
    description="Retourne toutes les sessions en cours avec leurs métriques.",
)
async def lister_sessions() -> list[SessionActive]:
    """Retourne un snapshot thread-safe des sessions actives."""
    return lister_sessions_actives()


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
    summary="Détail d'une session",
    description="Retourne les métadonnées complètes et les derniers événements.",
)
async def detail_session(session_id: str) -> SessionDetail:
    """404 si la session est introuvable ou expirée."""
    from shared.state import lister_sessions_actives
    from analyse.pipeline import pipeline
    
    sessions = lister_sessions_actives()
    session_data = next((s for s in sessions if s.get('session_id') == session_id), None)
    
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' introuvable ou expirée.",
        )
    
    # Enrichir avec l'historique du pipeline
    if pipeline.dataframe is not None and not pipeline.dataframe.empty:
        historique = pipeline.dataframe[pipeline.dataframe['session_id'] == session_id]
        derniers = historique.tail(50).to_dict('records')
    else:
        derniers = []
        
    return SessionDetail(
        **session_data,
        derniers_evenements=derniers
    )


@router.delete(
    "/{identifier}",
    summary="Forcer la déconnexion d'un utilisateur",
    description="Révoque une session active par session_id ou adresse IP.",
    dependencies=[Depends(_verifier_token_admin)],
)
async def deconnecter_session(identifier: str) -> dict:
    """
    Révoque la session. L'identifiant peut être un UUID de session ou une adresse IP.
    """
    sessions_list = lister_sessions_actives()
    # Recherche par ID ou par IP
    session = next((s for s in sessions_list if s.get('session_id') == identifier or s.get('ip_client') == identifier), None)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session ou IP '{identifier}' introuvable.",
        )
    
    ip_client = session.get('ip_client')
    user_id = session.get('user_id', 'Anonyme')
    session_id = session.get('session_id')
    
    succes = revoquer_session(ip_client, reason="déconnexion forcée par admin")
    if not succes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la révocation de session.",
        )
    logger.info("Session révoquée par admin — identifier=%s ip=%s", identifier, ip_client)
    return {
        "message": f"Session {session_id} révoquée avec succès.",
        "ip": ip_client,
        "user_id": user_id,
    }