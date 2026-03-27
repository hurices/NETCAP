"""
tests/test_shared.py
Tests unitaires pour l'état partagé.
"""

import pytest
from datetime import datetime, timedelta
from shared.state import SharedState, state


class TestSharedState:
    """Tests pour la classe SharedState"""

    def setup_method(self):
        """Réinitialise l'état avant chaque test"""
        self.state = SharedState()
        self.state.reset_stats()

    def test_add_and_get_session(self):
        """Test d'ajout et récupération d'une session"""
        session = {
            "token": "test-token-123",
            "user_id": "user@test.com",
            "user_name": "Test User",
            "expires_at": datetime.now() + timedelta(minutes=30)
        }
        self.state.add_session("192.168.1.1", session)
        retrieved = self.state.get_session("192.168.1.1")

        assert retrieved is not None
        assert retrieved["token"] == "test-token-123"
        assert retrieved["user_name"] == "Test User"

    def test_remove_session(self):
        """Test de suppression d'une session"""
        session = {
            "token": "test-token",
            "expires_at": datetime.now() + timedelta(minutes=30)
        }
        self.state.add_session("192.168.1.1", session)
        removed = self.state.remove_session("192.168.1.1")

        assert removed == session
        assert self.state.get_session("192.168.1.1") is None

    def test_get_session_by_token(self):
        """Test de récupération par token"""
        session = {
            "token": "test-token-456",
            "expires_at": datetime.now() + timedelta(minutes=30)
        }
        self.state.add_session("192.168.1.1", session)
        retrieved = self.state.get_session_by_token("test-token-456")

        assert retrieved == session

    def test_get_all_sessions(self):
        """Test de récupération de toutes les sessions"""
        session1 = {"token": "token1", "expires_at": datetime.now() + timedelta(minutes=30)}
        session2 = {"token": "token2", "expires_at": datetime.now() + timedelta(minutes=30)}

        self.state.add_session("192.168.1.1", session1)
        self.state.add_session("192.168.1.2", session2)

        all_sessions = self.state.get_all_sessions()
        assert len(all_sessions) == 2
        assert "192.168.1.1" in all_sessions
        assert "192.168.1.2" in all_sessions

    def test_cleanup_expired_sessions(self):
        """Test de nettoyage des sessions expirées"""
        session_valid = {
            "token": "valid",
            "expires_at": datetime.now() + timedelta(minutes=30)
        }
        session_expired = {
            "token": "expired",
            "expires_at": datetime.now() - timedelta(minutes=1)
        }

        self.state.add_session("192.168.1.1", session_valid)
        self.state.add_session("192.168.1.2", session_expired)

        count = self.state.cleanup_expired_sessions()
        assert count == 1
        assert self.state.get_session("192.168.1.1") is not None
        assert self.state.get_session("192.168.1.2") is None

    def test_update_session_activity(self):
        """Test de mise à jour de l'activité"""
        session = {
            "token": "test",
            "expires_at": datetime.now() + timedelta(minutes=30),
            "last_activity": datetime.now() - timedelta(minutes=5)
        }
        self.state.add_session("192.168.1.1", session)

        old_activity = session["last_activity"]
        self.state.update_session_activity("192.168.1.1")
        new_activity = self.state.get_session("192.168.1.1")["last_activity"]

        assert new_activity > old_activity

    def test_add_event(self):
        """Test d'ajout d'événement dans la queue"""
        event = {
            "ip_client": "192.168.1.1",
            "domain": "google.com",
            "method": "GET"
        }
        result = self.state.add_event(event)
        assert result is True
        assert self.state.queue_size() == 1

    def test_get_event(self):
        """Test de récupération d'événement"""
        event = {"ip_client": "192.168.1.1", "domain": "google.com"}
        self.state.add_event(event)

        retrieved = self.state.get_event(timeout=0.1)
        assert retrieved is not None
        assert retrieved["domain"] == "google.com"
        assert "timestamp" in retrieved  # Timestamp auto-ajouté

    def test_queue_full(self):
        """Test de comportement quand la queue est pleine"""
        # Créer une nouvelle instance avec petite queue pour test
        small_state = SharedState()
        small_state._event_queue = Queue(maxsize=2)

        assert small_state.add_event({"event": 1}) is True
        assert small_state.add_event({"event": 2}) is True
        assert small_state.add_event({"event": 3}) is False  # Queue pleine

    def test_stop_and_is_running(self):
        """Test d'arrêt du système"""
        assert self.state.is_running() is True
        self.state.stop()
        assert self.state.is_running() is False

    def test_get_uptime(self):
        """Test de calcul de l'uptime"""
        assert self.state.get_uptime_seconds() >= 0
        assert isinstance(self.state.get_uptime_formatted(), str)

    def test_get_stats(self):
        """Test des statistiques"""
        # Ajouter des sessions
        session = {"token": "test", "expires_at": datetime.now() + timedelta(minutes=30)}
        self.state.add_session("192.168.1.1", session)

        # Ajouter des événements
        self.state.add_event({"size_bytes": 100})
        self.state.add_event({"size_bytes": 200})

        stats = self.state.get_stats()

        assert stats["active_sessions"] == 1
        assert stats["queue_size"] == 2
        assert stats["total_requests"] == 2
        assert stats["total_bytes"] == 300
        assert stats["total_bytes_mb"] == pytest.approx(0.000286, rel=1e-3)
        assert stats["running"] is True

    def test_serialization(self):
        """Test de sérialisation des données"""
        session = {
            "token": "test",
            "expires_at": datetime.now() + timedelta(minutes=30)
        }
        self.state.add_session("192.168.1.1", session)

        # Vérifier que les dates sont sérialisables
        stored = self.state.get_session("192.168.1.1")
        assert "expires_at" in stored
        assert isinstance(stored["expires_at"], datetime)


class TestStateSingleton:
    """Tests pour l'instance singleton"""

    def test_state_is_singleton(self):
        """Vérifie que state est bien une instance unique"""
        from shared.state import state as state1
        from shared.state import state as state2
        assert state1 is state2

    def test_state_is_shared_state_instance(self):
        """Vérifie que state est une instance de SharedState"""
        from shared.state import state
        assert isinstance(state, SharedState)