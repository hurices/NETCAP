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

import config
from api.schemas import AlerteAnomalie, CategoryEnum

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
        self.zscore_threshold = zscore_threshold or config.ANOMALIE_ZSCORE_SEUIL
        self.max_volume_mb = max_volume_mb or config.ANOMALIE_VOLUME_MAX_SESSION_MB
        self.min_samples = config.ANOMALIE_MIN_SAMPLES

        self.alerts: List[AlerteAnomalie] = []
        self._last_check = datetime.now()

        logger.info(f"DetecteurAnomalies initialisé: seuil Z-score={self.zscore_threshold}, "
                    f"volume max={self.max_volume_mb}MB, min_samples={self.min_samples}")

    def detecter(self, dataframe) -> List[AlerteAnomalie]:
        """
        Détecte les anomalies dans le DataFrame.
        Utilise NumPy pour le calcul vectorisé du Z-score.
        """
        import numpy as np
        from shared.state import ajouter_alerte
        import uuid

        if dataframe is None or len(dataframe) < self.min_samples:
            return []

        # Grouper par utilisateur pour avoir le volume total par session
        stats_user = dataframe.groupby('user_id')['taille_bytes'].sum() / (1024 * 1024)  # MB
        
        users = stats_user.index.tolist()
        volumes = stats_user.values
        
        mean_v = np.mean(volumes)
        std_v = np.std(volumes)
        
        if std_v == 0:
            std_v = 1e-6  # Éviter division par zéro

        z_scores = (volumes - mean_v) / std_v
        
        new_alerts = []
        for i, z in enumerate(z_scores):
            user_id = users[i]
            volume = volumes[i]
            
            # Vérifier si Z-score dépasse le seuil OU si volume > max absolu
            if abs(z) > self.zscore_threshold or volume > self.max_volume_mb:
                # Créer une alerte
                alerte = AlerteAnomalie(
                    alerte_id=str(uuid.uuid4()),
                    user_id=user_id,
                    ip_client=dataframe[dataframe['user_id'] == user_id]['ip_client'].iloc[0],
                    score_zscore=float(z),
                    volume_session=int(volume * 1024 * 1024),
                    volume_moyen_groupe=float(mean_v * 1024 * 1024),
                    timestamp_detection=datetime.now(),
                    details=f"Volume anormal: {volume:.2f} MB (Z-score: {z:.2f})",
                    acquittee=False
                )
                
                # Éviter les alertes en double pour la même session/utilisateur trop rapprochées
                last_alerts = [a for a in self.alerts if a.user_id == user_id]
                if not last_alerts or (datetime.now() - last_alerts[-1].timestamp_detection).seconds > 300:
                    self.alerts.append(alerte)
                    new_alerts.append(alerte)
                    # Sauvegarder dans l'état partagé
                    ajouter_alerte(alerte.model_dump())
                    logger.warning(f"ANOMALIE DÉTECTÉE: User={user_id}, Z={z:.2f}, Vol={volume:.2f}MB")
        
        self._last_check = datetime.now()
        return new_alerts

    def _calculate_zscore(self, values: List[float]) -> List[float]:
        """Calcule le Z-score avec NumPy."""
        import numpy as np
        if not values:
            return []
        arr = np.array(values)
        mean = np.mean(arr)
        std = np.std(arr)
        if std == 0:
            return [0.0] * len(values)
        return ((arr - mean) / std).tolist()

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

    def get_alerts(self) -> List[AlerteAnomalie]:
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