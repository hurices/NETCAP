"""
tests/test_schemas.py
Tests unitaires pour les modèles Pydantic.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
from api.schemas import (
    UserRegistration, SessionData, NavigationEvent,
    CategoryEnum, HTTPMethodEnum, DomainStats, TrafficMetrics,
    SessionInfo, AnomalyAlert, AlertConfig, HealthStatus
)


class TestUserRegistration:
    """Tests pour UserRegistration"""

    def test_valid_user(self):
        """Test avec données valides"""
        user = UserRegistration(
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@example.com",
            accepts_cgu=True
        )
        assert user.first_name == "Jean"
        assert user.last_name == "Dupont"
        assert user.email == "jean.dupont@example.com"
        assert user.full_name == "Jean Dupont"
        assert user.accepts_analytics is False

    def test_missing_cgu_raises_error(self):
        """Test que l'acceptation des CGU est obligatoire"""
        with pytest.raises(ValidationError) as exc_info:
            UserRegistration(
                first_name="Jean",
                last_name="Dupont",
                email="jean@example.com",
                accepts_cgu=False
            )
        assert "accepter les Conditions Générales" in str(exc_info.value)

    def test_invalid_email_raises_error(self):
        """Test de validation d'email invalide"""
        with pytest.raises(ValidationError):
            UserRegistration(
                first_name="Jean",
                last_name="Dupont",
                email="not-an-email",
                accepts_cgu=True
            )

    def test_invalid_name_raises_error(self):
        """Test de validation de nom avec caractères invalides"""
        with pytest.raises(ValidationError):
            UserRegistration(
                first_name="Jean123",
                last_name="Dupont",
                email="jean@example.com",
                accepts_cgu=True
            )

    def test_valid_name_with_accents(self):
        """Test des noms avec accents"""
        user = UserRegistration(
            first_name="Jean-Philippe",
            last_name="Dupont-Renard",
            email="jean@example.com",
            accepts_cgu=True
        )
        assert user.full_name == "Jean-Philippe Dupont-Renard"

    def test_optional_analytics(self):
        """Test d'acceptation optionnelle de l'analyse"""
        user = UserRegistration(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            accepts_cgu=True,
            accepts_analytics=True
        )
        assert user.accepts_analytics is True


class TestSessionData:
    """Tests pour SessionData"""

    def test_session_creation(self):
        """Test de création de session"""
        user = UserRegistration(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            accepts_cgu=True
        )
        session = SessionData.create(user, "192.168.1.1", 30)

        assert session.user_id == "jean@example.com"
        assert session.user_name == "Jean Dupont"
        assert session.ip_client == "192.168.1.1"
        assert session.is_expired() is False
        assert session.remaining_minutes() <= 30
        assert session.remaining_minutes() >= 29

    def test_session_expiration(self):
        """Test de session expirée"""
        user = UserRegistration(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            accepts_cgu=True
        )
        session = SessionData.create(user, "192.168.1.1", 0)
        assert session.is_expired() is True
        assert session.remaining_seconds() == 0
        assert session.remaining_minutes() == 0

    def test_session_to_storage_dict(self):
        """Test de conversion en dictionnaire pour stockage"""
        user = UserRegistration(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            accepts_cgu=True
        )
        session = SessionData.create(user, "192.168.1.1", 30)
        storage = session.to_storage_dict()

        assert isinstance(storage, dict)
        assert "token" in storage
        assert "created_at" in storage
        assert "expires_at" in storage
        assert isinstance(storage["created_at"], str)

    def test_request_count_increment(self):
        """Test d'incrémentation du compteur"""
        user = UserRegistration(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            accepts_cgu=True
        )
        session = SessionData.create(user, "192.168.1.1", 30)
        assert session.request_count == 0

        session.request_count += 1
        assert session.request_count == 1


class TestNavigationEvent:
    """Tests pour NavigationEvent"""

    def test_domain_normalization(self):
        """Test de normalisation du domaine"""
        event = NavigationEvent(
            ip_client="192.168.1.1",
            method=HTTPMethodEnum.GET,
            domain="www.github.com"
        )
        assert event.domain == "github.com"

    def test_domain_normalization_lowercase(self):
        """Test de mise en minuscules"""
        event = NavigationEvent(
            ip_client="192.168.1.1",
            method=HTTPMethodEnum.GET,
            domain="GITHUB.COM"
        )
        assert event.domain == "github.com"

    def test_default_values(self):
        """Test des valeurs par défaut"""
        event = NavigationEvent(
            ip_client="192.168.1.1",
            method=HTTPMethodEnum.GET,
            domain="example.com"
        )
        assert event.url_path == "/"
        assert event.status_http == 200
        assert event.category == CategoryEnum.OTHER
        assert event.size_bytes == 0
        assert event.is_https is False
        assert event.timestamp is not None

    def test_https_request(self):
        """Test de requête HTTPS (CONNECT)"""
        event = NavigationEvent(
            ip_client="192.168.1.1",
            method=HTTPMethodEnum.CONNECT,
            domain="google.com",
            is_https=True
        )
        assert event.method == HTTPMethodEnum.CONNECT
        assert event.is_https is True

    def test_full_url_path(self):
        """Test avec chemin complet"""
        event = NavigationEvent(
            ip_client="192.168.1.1",
            method=HTTPMethodEnum.GET,
            domain="github.com",
            url_path="/user/repo/issues/123"
        )
        assert event.url_path == "/user/repo/issues/123"


class TestDomainStats:
    """Tests pour DomainStats"""

    def test_domain_stats_creation(self):
        """Test de création des statistiques par domaine"""
        stats = DomainStats(
            domain="google.com",
            category=CategoryEnum.SEARCH,
            request_count=100,
            total_bytes=1024000
        )
        assert stats.domain == "google.com"
        assert stats.request_count == 100
        assert stats.avg_bytes_per_request == 10240.0

    def test_avg_bytes_calculation(self):
        """Test du calcul de la moyenne"""
        stats = DomainStats(
            domain="test.com",
            category=CategoryEnum.OTHER,
            request_count=50,
            total_bytes=50000
        )
        assert stats.avg_bytes_per_request == 1000.0

    def test_zero_requests(self):
        """Test avec zéro requête"""
        stats = DomainStats(
            domain="test.com",
            category=CategoryEnum.OTHER,
            request_count=0,
            total_bytes=0
        )
        assert stats.avg_bytes_per_request == 0.0


class TestTrafficMetrics:
    """Tests pour TrafficMetrics"""

    def test_traffic_metrics_creation(self):
        """Test de création des métriques"""
        metrics = TrafficMetrics(
            period="1h",
            total_requests=1000,
            total_bytes=10485760,  # 10 MB
            top_domains=[],
            category_distribution={},
            hourly_activity=[],
            active_users=5,
            error_rate=2.5
        )
        assert metrics.total_bytes_mb == 10.0
        assert metrics.error_rate == 2.5

    def test_bytes_to_mb_conversion(self):
        """Test de conversion bytes -> MB"""
        metrics = TrafficMetrics(
            period="1h",
            total_requests=500,
            total_bytes=1048576,  # 1 MB
            active_users=1,
            error_rate=0
        )
        assert metrics.total_bytes_mb == 1.0


class TestAlertConfig:
    """Tests pour AlertConfig"""

    def test_default_values(self):
        """Test des valeurs par défaut"""
        config = AlertConfig()
        assert config.zscore_threshold == 3.0
        assert config.max_volume_per_session_mb == 100
        assert config.max_session_duration_minutes == 30
        assert config.blocked_categories == []

    def test_custom_values(self):
        """Test des valeurs personnalisées"""
        config = AlertConfig(
            zscore_threshold=2.5,
            max_volume_per_session_mb=200,
            max_session_duration_minutes=60,
            blocked_categories=[CategoryEnum.STREAMING_VIDEO]
        )
        assert config.zscore_threshold == 2.5
        assert config.max_volume_per_session_mb == 200
        assert len(config.blocked_categories) == 1

    def test_validation_negative_values(self):
        """Test de validation des valeurs négatives"""
        with pytest.raises(ValidationError):
            AlertConfig(zscore_threshold=-1)

        with pytest.raises(ValidationError):
            AlertConfig(max_volume_per_session_mb=-10)


class TestHealthStatus:
    """Tests pour HealthStatus"""

    def test_health_status(self):
        """Test du statut de santé"""
        health = HealthStatus(
            status="healthy",
            components={"proxy": True, "flask": True, "api": True},
            active_sessions=5,
            dataframe_size=1000,
            queue_size=42,
            uptime_seconds=3600,
            uptime_formatted="01:00:00"
        )
        assert health.status == "healthy"
        assert health.uptime_formatted == "01:00:00"