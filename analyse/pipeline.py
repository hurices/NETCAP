"""
analyse/pipeline.py
Thread consommateur de la Queue + DataFrame Pandas.
"""

import threading
import logging
import sys
import os
from datetime import datetime
from typing import Optional, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import shared.state as state
from api.schemas import EvenementNavigation, MetriqueTrafic, StatUtilisateur
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
        if self.consumer_thread and self.consumer_thread.is_alive():
            logger.warning("Le pipeline est déjà en cours d'exécution")
            return

        import pandas as pd
        logger.info(" Démarrage du pipeline d'analyse...")

        # Initialisation du DataFrame avec les colonnes attendues
        self.dataframe = pd.DataFrame(columns=[
            "timestamp", "ip_client", "user_id", "session_id",
            "methode", "domaine", "url_path", "categorie",
            "taille_bytes", "duree_ms", "statut_http", "est_https"
        ])

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
        self._archive_data()
        logger.info("Pipeline arrêté")

    def _consumer_loop(self) -> None:
        """
        Boucle principale du consommateur.
        """
        logger.info("Thread consommateur démarré")

        while state.is_running():
            try:
                event_dict = state.obtenir_evenement(timeout=config.CONSUMER_SLEEP_SECONDS)
                if event_dict:
                    self._process_event(event_dict)
            except Exception as e:
                logger.error(f"Erreur dans le consommateur: {e}")

        logger.info("Thread consommateur arrêté")

    def _archive_data(self) -> None:
        """Archive les données."""
        pass

    def _process_event(self, event_dict: dict) -> None:
        """
        Traite un événement de navigation.
        Compatible avec les événements émis par le proxy du Sprint 2.
        """
        import pandas as pd
        try:
            # 1. Mise en conformité avec le format attendu par le pipeline
            # Le proxy utilise 'content_length' au lieu de 'taille_bytes'
            if 'content_length' in event_dict and 'taille_bytes' not in event_dict:
                event_dict['taille_bytes'] = event_dict.pop('content_length')
            
            # Gestion des champs optionnels
            event_dict.setdefault('user_id', 'Anonyme')
            event_dict.setdefault('session_id', 'Inconnue')
            event_dict.setdefault('statut_http', 200)
            event_dict.setdefault('est_https', False)
            event_dict.setdefault('taille_bytes', 0)
            
            # 2. Catégorisation
            domaine = event_dict.get('domaine', '')
            categorie = self.categoriseur.categoriser(domaine)
            event_dict['categorie'] = categorie.value
            
            # 3. Ajout au DataFrame
            new_row = pd.DataFrame([event_dict])
            self.dataframe = pd.concat([self.dataframe, new_row], ignore_index=True)
            
            # Limiter la taille du DataFrame (fenêtre glissante)
            if len(self.dataframe) > config.MAX_DATAFRAME_SIZE:
                self.dataframe = self.dataframe.iloc[-config.MAX_DATAFRAME_SIZE:]

            self.processed_events += 1

            # 4. Vérifier les anomalies tous les N événements
            if self.processed_events % 5 == 0:
                self.detecteur.detecter(self.dataframe)
                self._update_metrics()

        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'événement: {e}")

    def _update_metrics(self) -> None:
        """
        Calcule et met à jour les métriques agrégées.
        """
        if self.dataframe.empty:
            return

        # Top domaines
        top_dom = self.dataframe['domaine'].value_counts().head(10).to_dict()
        
        # Répartition catégories
        rep_cat = self.dataframe['categorie'].value_counts().to_dict()
        
        self._metrics_cache = {
            "top_domaines": [{"domaine": k, "count": v} for k, v in top_dom.items()],
            "repartition_categories": rep_cat,
            "total_requetes": len(self.dataframe),
            "total_bytes": int(self.dataframe['taille_bytes'].sum()),
            "utilisateurs_actifs": self.dataframe['user_id'].nunique(),
            "updated_at": datetime.now()
        }

    def get_metrics(self, periode: str = "1h") -> MetriqueTrafic:
        """
        Retourne les métriques agrégées pour une période donnée.
        """
        import pandas as pd
        now = datetime.now()
        
        # TODO: Filtrer par période (Sprint 4)
        # Pour l'instant on retourne tout ce qu'on a en cache
        
        metrics = self._metrics_cache
        if not metrics:
            return MetriqueTrafic(
                periode=periode,
                debut_periode=now,
                fin_periode=now,
                total_requetes=0,
                total_bytes=0,
                requetes_par_minute=0.0,
                taux_erreur_pct=0.0,
                top_domaines=[],
                repartition_categories={},
                utilisateurs_actifs=0
            )

        return MetriqueTrafic(
            periode=periode,
            debut_periode=metrics.get('updated_at', now), # Simplifié
            fin_periode=now,
            total_requetes=metrics['total_requetes'],
            total_bytes=metrics['total_bytes'],
            requetes_par_minute=metrics['total_requetes'] / 60.0, # Estimation
            taux_erreur_pct=float((self.dataframe['statut_http'] >= 400).mean() * 100),
            top_domaines=metrics['top_domaines'],
            repartition_categories=metrics['repartition_categories'],
            utilisateurs_actifs=metrics['utilisateurs_actifs']
        )

    def get_user_stats(self) -> List[StatUtilisateur]:
        """Retourne les stats par utilisateur."""
        if self.dataframe.empty:
            return []
            
        stats = self.dataframe.groupby('user_id').agg({
            'taille_bytes': 'sum',
            'timestamp': 'max',
            'domaine': 'count'
        }).reset_index()
        
        result = []
        for _, row in stats.iterrows():
            # Trouver la catégorie dominante pour cet utilisateur
            cat_dom = self.dataframe[self.dataframe['user_id'] == row['user_id']]['categorie'].mode()
            top_cat = cat_dom.iloc[0] if not cat_dom.empty else "Autre"
            
            result.append(StatUtilisateur(
                user_id=row['user_id'],
                total_requetes=row['domaine'],
                total_bytes=int(row['taille_bytes']),
                derniere_activite=row['timestamp'],
                top_categorie=top_cat
            ))
        return result

    def get_status(self) -> dict:
        """
        Retourne le statut du pipeline.
        """
        return {
            "running": self.consumer_thread is not None and self.consumer_thread.is_alive(),
            "processed_events": self.processed_events,
            "dataframe_size": len(self.dataframe) if self.dataframe is not None else 0,
            "queue_size": state.taille_queue(),
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