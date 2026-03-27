"""

Structures partagées entre tous les composants de NetCapt.

Ce module implémente le pattern Singleton pour l'état global du système.
Tous les composants accèdent aux mêmes structures via l'instance 'state'.
La thread-safety est assurée par des verrous (RLock, Queue thread-safe).
"""

from queue import Queue, Full, Empty
from threading import RLock
from typing import Dict, Optional, List, Any
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class SharedState:
    """
    État global du système partagé entre tous les composants.

    Thread-safety:
        - Les sessions sont protégées par un RLock (permet les appels récursifs)
        - La queue est thread-safe par nature (Queue de Python)
        - Le flag running est protégé par un RLock

    Attributs:
        sessions: Dict[str, dict] - Sessions actives indexées par IP
        sessions_by_token: Dict[str, str] - Index token -> IP
        event_queue: Queue - File d'attente des événements de navigation
        running: bool - Flag d'état du système
        start_time: datetime - Heure de démarrage
        dataframe: Any - DataFrame Pandas (initialisé par le pipeline)
        metrics_cache: dict - Cache des métriques calculées
    """

    def __init__(self):
        # ==================== GESTION DES SESSIONS ====================
        self._sessions: Dict[str, dict] = {}
        self._sessions_by_token: Dict[str, str] = {}
        self._sessions_lock = RLock()

        # ==================== FILE D'ATTENTE ====================
        self._event_queue: Queue = Queue(maxsize=10000)

        # ==================== ÉTAT SYSTÈME ====================
        self._running: bool = True
        self._running_lock = RLock()

        # ==================== MÉTADONNÉES ====================
        self.start_time: datetime = datetime.now()
        self.dataframe: Any = None  # Sera initialisé par le pipeline
        self.metrics_cache: Dict[str, Any] = {}  # Cache des métriques
        self.last_cleanup: datetime = datetime.now()

        # ==================== STATISTIQUES ====================
        self.total_requests: int = 0
        self.total_bytes: int = 0
        self._stats_lock = RLock()

    # ==================== SESSIONS ====================

    def add_session(self, ip_client: str, session_data: dict) -> None:
        """
        Ajoute une session de manière thread-safe.

        Args:
            ip_client: Adresse IP du client
            session_data: Dictionnaire contenant les données de session
                         (token, user_id, user_name, expires_at, ...)

        Raises:
            KeyError: Si session_data ne contient pas le champ 'token'
        """
        if 'token' not in session_data:
            raise KeyError("session_data doit contenir un champ 'token'")

        with self._sessions_lock:
            self._sessions[ip_client] = session_data
            self._sessions_by_token[session_data['token']] = ip_client
            logger.info(
                f" Session ajoutée | IP: {ip_client} | "
                f"Utilisateur: {session_data.get('user_name', 'N/A')} | "
                f"Expire: {session_data.get('expires_at', 'N/A')}"
            )

    def get_session(self, ip_client: str) -> Optional[dict]:
        """
        Récupère une session par IP.

        Args:
            ip_client: Adresse IP du client

        Returns:
            Données de session ou None si inexistante
        """
        with self._sessions_lock:
            return self._sessions.get(ip_client)

    def get_session_by_token(self, token: str) -> Optional[dict]:
        """
        Récupère une session par token.

        Args:
            token: Token de session UUID

        Returns:
            Données de session ou None si inexistante
        """
        with self._sessions_lock:
            ip_client = self._sessions_by_token.get(token)
            if ip_client:
                return self._sessions.get(ip_client)
            return None

    def remove_session(self, ip_client: str) -> Optional[dict]:
        """
        Supprime une session et retourne ses données.

        Args:
            ip_client: Adresse IP du client

        Returns:
            Données de session supprimées ou None
        """
        with self._sessions_lock:
            session = self._sessions.pop(ip_client, None)
            if session:
                self._sessions_by_token.pop(session['token'], None)
                logger.info(f"Session supprimée | IP: {ip_client}")
            return session

    def update_session_activity(self, ip_client: str) -> None:
        """Met à jour le timestamp de dernière activité d'une session."""
        with self._sessions_lock:
            session = self._sessions.get(ip_client)
            if session:
                session['last_activity'] = datetime.now()

    def get_all_sessions(self) -> Dict[str, dict]:
        """Retourne une copie de toutes les sessions."""
        with self._sessions_lock:
            return self._sessions.copy()

    def get_active_sessions_count(self) -> int:
        """Retourne le nombre de sessions actives."""
        with self._sessions_lock:
            return len(self._sessions)

    def cleanup_expired_sessions(self) -> int:
        """
        Supprime toutes les sessions expirées.

        Returns:
            Nombre de sessions supprimées
        """
        now = datetime.now()
        expired_ips: List[str] = []

        with self._sessions_lock:
            for ip_client, session in self._sessions.items():
                expires_at = session.get('expires_at')
                if expires_at:
                    # Support des strings ISO et des objets datetime
                    if isinstance(expires_at, str):
                        try:
                            expires_at = datetime.fromisoformat(expires_at)
                        except ValueError:
                            continue
                    if expires_at < now:
                        expired_ips.append(ip_client)

            for ip_client in expired_ips:
                session = self._sessions.pop(ip_client, None)
                if session:
                    self._sessions_by_token.pop(session['token'], None)

        if expired_ips:
            logger.info(f" Nettoyage | {len(expired_ips)} sessions expirées supprimées")

        self.last_cleanup = now
        return len(expired_ips)

    # ==================== FILE D'ÉVÉNEMENTS ====================

    def add_event(self, event: dict) -> bool:
        """
        Ajoute un événement dans la queue (non-bloquant).

        Args:
            event: Dictionnaire représentant un événement de navigation

        Returns:
            True si ajouté, False si la queue est pleine
        """
        # Ajout d'un timestamp si absent
        if 'timestamp' not in event:
            event['timestamp'] = datetime.now().isoformat()

        try:
            self._event_queue.put_nowait(event)
            # Mise à jour des statistiques
            with self._stats_lock:
                self.total_requests += 1
                self.total_bytes += event.get('size_bytes', 0)
            return True
        except Full:
            logger.warning("Queue pleine, événement perdu")
            return False

    def get_event(self, timeout: float = 0.1) -> Optional[dict]:
        """
        Récupère un événement de la queue (bloquant avec timeout).

        Args:
            timeout: Temps d'attente maximum en secondes

        Returns:
            Événement ou None si timeout
        """
        try:
            return self._event_queue.get(timeout=timeout)
        except Empty:
            return None

    def queue_size(self) -> int:
        """Retourne le nombre d'événements en attente."""
        return self._event_queue.qsize()

    def queue_is_full(self) -> bool:
        """Vérifie si la queue est pleine."""
        return self._event_queue.full()

    # ==================== CONTRÔLE SYSTÈME ====================

    def stop(self) -> None:
        """Arrête le système (tous les composants)."""
        with self._running_lock:
            self._running = False
        logger.info("Signal d'arrêt envoyé à tous les composants")

    def is_running(self) -> bool:
        """Vérifie si le système doit continuer à fonctionner."""
        with self._running_lock:
            return self._running

    # ==================== MÉTRIQUES ====================

    def get_uptime_seconds(self) -> float:
        """Retourne le temps d'activité en secondes."""
        return (datetime.now() - self.start_time).total_seconds()

    def get_uptime_formatted(self) -> str:
        """Retourne le temps d'activité formaté (HH:MM:SS)."""
        seconds = int(self.get_uptime_seconds())
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques rapides sur l'état du système.

        Returns:
            Dictionnaire avec:
            - active_sessions: nombre de sessions actives
            - queue_size: taille de la file d'événements
            - uptime_seconds: temps d'activité
            - uptime_formatted: temps d'activité formaté
            - total_requests: nombre total de requêtes
            - total_bytes: volume total en octets
            - running: état du système
        """
        with self._sessions_lock:
            active_sessions = len(self._sessions)

        with self._stats_lock:
            total_requests = self.total_requests
            total_bytes = self.total_bytes

        return {
            "active_sessions": active_sessions,
            "queue_size": self.queue_size(),
            "uptime_seconds": self.get_uptime_seconds(),
            "uptime_formatted": self.get_uptime_formatted(),
            "total_requests": total_requests,
            "total_bytes": total_bytes,
            "total_bytes_mb": round(total_bytes / (1024 * 1024), 2),
            "running": self.is_running(),
            "start_time": self.start_time.isoformat()
        }

    def reset_stats(self) -> None:
        """Réinitialise les statistiques (pour les tests)."""
        with self._stats_lock:
            self.total_requests = 0
            self.total_bytes = 0


# Instance unique partagée par tous les composants
state = SharedState()