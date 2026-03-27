"""
analyse/detecteur_anomalies.py
Détection d'anomalies comportementales (Z-score).

Sprint 1: Définition des structures.
Sprint 4: Implémentation complète avec NumPy.

Auteur: Équipe NetCapt
Date: Sprint 1 - Mars 2026
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from config import config
from api.schemas import AnomalyAlert, CategoryEnum

logger = logging.getLogger(__name__)


class DetecteurAnomalies:
    """
    Détecteur d'anomalies basé sur le calcul du Z-score.

    Principe:
    - Calcule le volume moyen par utilisateur
    - Identifie les utilisateurs dont le volume dépasse le seuil configuré
    - Génère des alertes pour les comportements suspects
    """

    def __init__(self, zscore_threshold: float = None, max_volume_mb: int = None):
        """
        Initialise le détecteur avec les seuils configurés.

        Args:
            zscore_threshold: Seuil Z-score (défaut: config.ANOMALY_ZSCORE_THRESHOLD)
            max_volume_mb: Volume max par session en MB (défaut: config.ANOMALY_VOLUME_MAX_MB)
        """
        self.zscore_threshold = zscore_threshold or config.ANOMALY_ZSCORE_THRESHOLD
        self.max_volume_mb = max_volume_mb or config.ANOMALY_VOLUME_MAX_MB
        self.min_samples = config.ANOMALY_MIN_SAMPLES

        self.alerts: List[AnomalyAlert] = []
        self._last_check = datetime.now()

        logger.info(f"DetecteurAnomalies initialisé: seuil Z-score={self.zscore_threshold}, "
                    f"volume max={self.max_volume_mb}MB, min_samples={self.min_samples}")

    def detecter(self, dataframe) -> List[AnomalyAlert]:
        """
        Détecte les anomalies dans le DataFrame.

        Args:
            dataframe: DataFrame Pandas contenant les événements

        Returns:
            Liste des alertes d'anomalies
        """
        # TODO Sprint 4: Implémentation avec NumPy
        logger.debug("Détection d'anomalies (Sprint 4)")
        return []

    def _calculate_zscore(self, values: List[float]) -> List[float]:
        """
        Calcule le Z-score pour une liste de valeurs.

        Z-score = (x - μ) / σ
        où μ = moyenne, σ = écart-type

        Args:
            values: Liste des valeurs

        Returns:
            Liste des Z-scores
        """
        # TODO Sprint 4: Implémentation NumPy
        return []

    def _is_anomaly(self, volume_mb: float, mean_volume: float, std_volume: float) -> bool:
        """
        Détermine si un volume est anormal.

        Args:
            volume_mb: Volume de la session en MB
            mean_volume: Volume moyen du groupe en MB
            std_volume: Écart-type du groupe

        Returns:
            True si anomalie détectée
        """
        if std_volume == 0:
            return volume_mb > self.max_volume_mb

        zscore = (volume_mb - mean_volume) / std_volume
        return abs(zscore) > self.zscore_threshold

    def get_alerts(self) -> List[AnomalyAlert]:
        """Retourne toutes les alertes générées."""
        return self.alerts.copy()

    def clear_alerts(self) -> None:
        """Efface toutes les alertes."""
        self.alerts.clear()
        logger.info("Alertes effacées")

    def get_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur la détection."""
        return {
            "threshold_zscore": self.zscore_threshold,
            "max_volume_mb": self.max_volume_mb,
            "min_samples": self.min_samples,
            "total_alerts": len(self.alerts),
            "last_check": self._last_check.isoformat()
        }