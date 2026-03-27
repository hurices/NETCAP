"""
analyse/pipeline.py
Thread consommateur de la Queue + DataFrame Pandas.
"""

import threading
import logging
import sys
import os
from datetime import datetime
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from shared.state import state
from api.schemas import NavigationEvent, TrafficMetrics
from analyse.categoriseur import Categoriseur
from analyse.detecteur_anomalies import DetecteurAnomalies

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """
    Pipeline d'analyse en continu.

    Responsabilités:
    - Consomme les événements de la Queue
    - Alimente un DataFrame Pandas
    - Calcule des métriques en temps réel
    - Détecte les anomalies
    - Archive les données anciennes
    """

    def __init__(self):
        self.consumer_thread: Optional[threading.Thread] = None
        self.dataframe = None  # DataFrame Pandas (initialisé au démarrage)
        self.categoriseur = Categoriseur()
        self.detecteur = DetecteurAnomalies()

        # Métriques en cache
        self._metrics_cache: dict = {}
        self._last_metrics_update = None

        # Statistiques
        self.processed_events = 0
        self.last_archive = datetime.now()

        logger.info("AnalysisPipeline initialisé (Sprint 1)")

    def start(self) -> None:
        """
        Démarre le thread consommateur.
        Appelé après initialisation de l'API et du portail.
        """
        logger.info(" Démarrage du pipeline d'analyse...")

        # TODO Sprint 3: Initialiser le DataFrame
        # self.dataframe = pd.DataFrame(columns=[
        #     "timestamp", "ip_client", "user_id", "session_token",
        #     "method", "domain", "url_path", "category",
        #     "size_bytes", "duration_ms", "status_http", "is_https"
        # ])

        self.consumer_thread = threading.Thread(
            target=self._consumer_loop,
            daemon=True,
            name="PipelineConsumer"
        )
        self.consumer_thread.start()

        logger.info(" Pipeline d'analyse démarré")

    def stop(self) -> None:
        """Arrête le pipeline."""
        logger.info(" Arrêt du pipeline d'analyse...")
        # Le thread daemon s'arrêtera automatiquement
        self._archive_data()
        logger.info("Pipeline arrêté")

    def _consumer_loop(self) -> None:
        """
        Boucle principale du consommateur.
        Tourne en continu et traite les événements.
        """
        logger.info("Thread consommateur démarré")

        while state.is_running():
            try:
                event_dict = state.get_event(timeout=config.CONSUMER_SLEEP_SECONDS)

                if event_dict:
                    self._process_event(event_dict)

            except Exception as e:
                logger.error(f"Erreur dans le consommateur: {e}")

        logger.info("Thread consommateur arrêté")

    def _process_event(self, event_dict: dict) -> None:
        """
        Traite un événement de navigation.

        Args:
            event_dict: Dictionnaire représentant l'événement
        """
        # TODO Sprint 3: Implémentation complète
        # 1. Valider avec Pydantic
        # 2. Catégoriser le domaine
        # 3. Ajouter au DataFrame
        # 4. Mettre à jour les métriques
        # 5. Vérifier les anomalies

        self.processed_events += 1

        if self.processed_events % 100 == 0:
            logger.debug(f"Événements traités: {self.processed_events}")

    def _update_metrics(self) -> None:
        """
        Calcule et met à jour les métriques agrégées.
        Appelé périodiquement ou après chaque batch.
        """
        # TODO Sprint 3: Calcul des métriques
        # - Top 10 domaines
        # - Répartition par catégorie
        # - Activité horaire
        # - Durée moyenne de session
        # - Taux d'erreur HTTP
        pass

    def _archive_data(self) -> None:
        """
        Archive les événements anciens dans un fichier CSV.
        Supprime les données au-delà de la fenêtre glissante.
        """
        # TODO Sprint 3: Archivage CSV
        pass

    def get_metrics(self, period: str = "1h") -> TrafficMetrics:
        """
        Retourne les métriques agrégées pour une période donnée.

        Args:
            period: Période (5m, 1h, 4h)

        Returns:
            TrafficMetrics avec les métriques calculées
        """
        # TODO Sprint 3: Implémentation
        return TrafficMetrics(
            period=period,
            total_requests=0,
            total_bytes=0,
            active_users=0,
            error_rate=0.0
        )

    def get_user_stats(self, user_id: str) -> dict:
        """
        Retourne les statistiques pour un utilisateur.

        Args:
            user_id: Identifiant de l'utilisateur

        Returns:
            Dictionnaire avec les statistiques
        """
        # TODO Sprint 3: Implémentation
        return {}

    def get_status(self) -> dict:
        """
        Retourne le statut du pipeline.

        Returns:
            Dictionnaire avec état et métriques
        """
        return {
            "running": self.consumer_thread is not None and self.consumer_thread.is_alive(),
            "processed_events": self.processed_events,
            "dataframe_size": 0,  # TODO Sprint 3
            "queue_size": state.queue_size(),
            "categoriseur_stats": self.categoriseur.get_stats(),
            "detecteur_stats": self.detecteur.get_stats()
        }


# Instance unique (peut être utilisée par d'autres composants)
pipeline = AnalysisPipeline()


def main():
    """Point d'entrée pour exécuter le pipeline seul."""
    try:
        pipeline.start()

        # Boucle principale
        while state.is_running():
            import time
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Arrêt demandé...")
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()