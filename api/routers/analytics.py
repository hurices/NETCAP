"""
Regroupe tous les endpoints analytiques.
Monté sur le préfixe /analytics dans api/main.py.

Sprint 1 : structure et documentation complète.
Sprint 4 : implémentation des calculs Pandas/NumPy.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.schemas import (
    AlerteAnomalie,
    MetriqueTrafic,
    PeriodeAnalyse,
    StatUtilisateur,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytique"])


@router.get(
    "/trafic",
    response_model=MetriqueTrafic,
    summary="Métriques agrégées du trafic",
    description=(
        "Retourne les métriques de navigation pour la période demandée : "
        "top domaines, répartition par catégorie, activité horaire, taux d'erreur."
    ),
)
async def analytics_trafic(
    periode: PeriodeAnalyse = Query(
        default=PeriodeAnalyse.UNE_HEURE,
        description="Fenêtre temporelle : 5m | 1h | 4h | 24h",
    ),
) -> MetriqueTrafic:
    """
    Retourne les métriques calculées par le pipeline d'analyse.
    """
    from analyse.pipeline import pipeline
    return pipeline.get_metrics(periode.value)


@router.get(
    "/utilisateurs",
    response_model=list[StatUtilisateur],
    summary="Statistiques par utilisateur",
    description=(
        "Retourne les métriques de navigation par utilisateur. "
        "Les données sont pseudonymisées par défaut."
    ),
)
async def analytics_utilisateurs() -> list[StatUtilisateur]:
    """
    Agrégation depuis le DataFrame Pandas par user_id.
    """
    from analyse.pipeline import pipeline
    return pipeline.get_user_stats()


@router.get(
    "/anomalies",
    response_model=list[AlerteAnomalie],
    summary="Anomalies comportementales détectées",
    description=(
        "Retourne les utilisateurs dont le score Z-score dépasse le seuil configuré."
    ),
)
async def analytics_anomalies(
    non_acquittees: bool = Query(
        default=False,
        description="Si True, retourne uniquement les alertes non encore acquittées",
    ),
) -> list[AlerteAnomalie]:
    """
    Récupère les alertes du détecteur d'anomalies.
    """
    from analyse.pipeline import pipeline
    from shared.state import lister_alertes
    
    alertes = lister_alertes()
    if non_acquittees:
        alertes = [a for a in alertes if not a.get('acquittee', False)]
    
    # Conversion dict -> Pydantic
    return [AlerteAnomalie(**a) for a in alertes]


@router.get(
    "/tendances",
    summary="Évolution du trafic sur les dernières heures",
)
async def analytics_tendances(
    heures: int = Query(default=4, ge=1, le=24),
) -> dict:
    """
    Analyse temporelle des tendances.
    """
    from analyse.pipeline import pipeline
    # Pour l'instant on retourne les métriques globales simplifiées
    metrics = pipeline.get_metrics()
    return {
        "heures_demandees": heures,
        "total_requetes": metrics.total_requetes,
        "total_bytes": metrics.total_bytes,
        "message": "Tendances calculées sur la fenêtre glissante du DataFrame."
    }


@router.get(
    "/alertes/{alerte_id}/acquitter",
    summary="Acquitter une alerte",
    description="Marque une alerte comme traitée par un administrateur.",
)
async def acquitter_alerte_endpoint(alerte_id: str) -> dict:
    """Acquitte une alerte par son UUID."""
    from shared.state import acquitter_alerte
    succes = acquitter_alerte(alerte_id)
    if not succes:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerte '{alerte_id}' introuvable.",
        )
    return {"message": f"Alerte {alerte_id} acquittée.", "alerte_id": alerte_id}