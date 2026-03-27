"""
api/schemas.py
Modèles Pydantic pour la validation des données NetCapt.

Ces modèles assurent l'intégrité et la cohérence des données échangées
entre les différents composants du système. Toute donnée entrante
est validée avant traitement.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
import re


class CategoryEnum(str, Enum):
    """
    Catégories de sites web pour la classification des domaines.
    Utilisée par le pipeline d'analyse pour générer des métriques.
    """
    SOCIAL = "Réseaux sociaux"
    STREAMING_VIDEO = "Streaming vidéo"
    STREAMING_AUDIO = "Streaming audio"
    DEVELOPMENT = "Développement"
    NEWS = "Actualités"
    SEARCH = "Moteurs de recherche"
    EMAIL = "Messagerie"
    ECOMMERCE = "E-commerce"
    EDUCATION = "Éducation"
    PRODUCTIVITY = "Productivité"
    OTHER = "Autre / Inconnu"


class HTTPMethodEnum(str, Enum):
    """Méthodes HTTP supportées par le proxy."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    CONNECT = "CONNECT"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"
    TRACE = "TRACE"


# ==================== MODÈLES PORTAIL ====================

class UserRegistration(BaseModel):
    """
    Formulaire d'inscription / authentification utilisateur.
    Reçu du formulaire HTML du portail.
    """
    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={
            "example": {
                "first_name": "Jean",
                "last_name": "Dupont",
                "email": "jean.dupont@example.com",
                "accepts_cgu": True,
                "accepts_analytics": False
            }
        }
    )

    first_name: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Prénom de l'utilisateur"
    )
    last_name: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Nom de l'utilisateur"
    )
    email: EmailStr = Field(
        ...,
        description="Adresse email valide"
    )
    accepts_cgu: bool = Field(
        ...,
        description="Acceptation obligatoire des CGU (conformité RGPD)"
    )
    accepts_analytics: bool = Field(
        False,
        description="Acceptation optionnelle de l'analyse des données"
    )

    @field_validator('accepts_cgu')
    @classmethod
    def must_accept_cgu(cls, v: bool) -> bool:
        """Valide que les CGU sont acceptées (exigence RGPD)."""
        if not v:
            raise ValueError("Vous devez accepter les Conditions Générales d'Utilisation")
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Valide le nom (caractères autorisés: lettres, espaces, tirets)."""
        if not re.match(r'^[a-zA-ZÀ-ÿ\s\-]+$', v):
            raise ValueError("Le nom ne doit contenir que des lettres, espaces et tirets")
        return v.strip()

    @property
    def full_name(self) -> str:
        """Retourne le nom complet formaté."""
        return f"{self.first_name} {self.last_name}"


class SessionData(BaseModel):
    """
    Données d'une session active.
    Stockée dans shared.state.sessions.
    """
    model_config = ConfigDict(extra='forbid')

    token: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Token unique de session (UUID v4)"
    )
    user_id: str = Field(..., description="Identifiant unique de l'utilisateur (email)")
    user_name: str = Field(..., description="Nom complet de l'utilisateur")
    user_email: EmailStr = Field(..., description="Email de l'utilisateur")
    ip_client: str = Field(..., description="Adresse IP du client")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Date et heure de création de la session"
    )
    expires_at: datetime = Field(..., description="Date et heure d'expiration")
    last_activity: datetime = Field(
        default_factory=datetime.now,
        description="Dernière activité du client"
    )
    request_count: int = Field(0, ge=0, description="Nombre de requêtes effectuées")
    total_bytes: int = Field(0, ge=0, description="Volume total en octets")

    def is_expired(self) -> bool:
        """Vérifie si la session a expiré."""
        return datetime.now() > self.expires_at

    def remaining_seconds(self) -> int:
        """Retourne le nombre de secondes restantes."""
        if self.is_expired():
            return 0
        return int((self.expires_at - datetime.now()).total_seconds())

    def remaining_minutes(self) -> int:
        """Retourne le nombre de minutes restantes."""
        return self.remaining_seconds() // 60

    @classmethod
    def create(
        cls, 
        user: UserRegistration, 
        ip_client: str, 
        duration_minutes: int
    ) -> "SessionData":
        """
        Crée une nouvelle session à partir d'un enregistrement utilisateur.

        Args:
            user: Données d'enregistrement utilisateur
            ip_client: Adresse IP du client
            duration_minutes: Durée de validité en minutes

        Returns:
            Instance de SessionData prête à être stockée
        """
        return cls(
            user_id=user.email,
            user_name=user.full_name,
            user_email=user.email,
            ip_client=ip_client,
            expires_at=datetime.now() + timedelta(minutes=duration_minutes)
        )

    def to_storage_dict(self) -> dict:
        """
        Convertit l'objet en dictionnaire sérialisable pour stockage.
        Utilisé pour le stockage dans shared.state.
        """
        return {
            "token": self.token,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "ip_client": self.ip_client,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "request_count": self.request_count,
            "total_bytes": self.total_bytes
        }


# ==================== MODÈLES ÉVÉNEMENTS ====================

class NavigationEvent(BaseModel):
    """
    Événement de navigation unique.
    Produit par le proxy, consommé par le pipeline.
    """
    model_config = ConfigDict(extra='allow')

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Horodatage précis de la requête"
    )
    ip_client: str = Field(..., description="Adresse IP du client")
    user_id: Optional[str] = Field(None, description="Identifiant utilisateur (si authentifié)")
    session_token: Optional[str] = Field(None, description="Token de session (si authentifié)")
    method: HTTPMethodEnum = Field(..., description="Méthode HTTP")
    domain: str = Field(..., description="Domaine cible (ex: google.com)")
    url_path: str = Field("/", description="Chemin de la ressource")
    category: CategoryEnum = Field(
        CategoryEnum.OTHER,
        description="Catégorie du domaine (déterminée par categoriseur)"
    )
    size_bytes: int = Field(0, ge=0, description="Volume en octets")
    duration_ms: int = Field(0, ge=0, description="Temps de réponse en millisecondes")
    status_http: int = Field(200, ge=100, lt=600, description="Code HTTP")
    is_https: bool = Field(False, description="Requête HTTPS (méthode CONNECT)")
    user_agent: Optional[str] = Field(None, description="User-Agent du navigateur")
    referer: Optional[str] = Field(None, description="Page d'origine")

    @field_validator('domain', mode='before')
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        """
        Normalise le domaine :
        - Met en minuscules
        - Supprime www.
        - Supprime les espaces
        """
        if not v:
            return ""
        v = v.lower().strip()
        if v.startswith('www.'):
            v = v[4:]
        return v


# ==================== MODÈLES MÉTRIQUES ====================

class DomainStats(BaseModel):
    """Statistiques par domaine."""
    domain: str
    category: CategoryEnum
    request_count: int = Field(..., ge=0)
    total_bytes: int = Field(..., ge=0)
    avg_bytes_per_request: float = Field(0.0, ge=0)

    def model_post_init(self, __context):
        """Calcule la moyenne après initialisation."""
        if self.request_count > 0:
            self.avg_bytes_per_request = self.total_bytes / self.request_count


class TrafficMetrics(BaseModel):
    """Métriques agrégées du trafic."""
    period: str = Field(..., description="Période (5m, 1h, 4h)")
    total_requests: int = Field(..., ge=0)
    total_bytes: int = Field(..., ge=0)
    total_bytes_mb: float = Field(0.0, ge=0)
    top_domains: List[DomainStats] = Field(default_factory=list)
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    hourly_activity: List[Dict[str, Any]] = Field(default_factory=list)
    active_users: int = Field(..., ge=0)
    error_rate: float = Field(..., ge=0, le=100)

    def model_post_init(self, __context):
        """Calcule les champs dérivés après initialisation."""
        self.total_bytes_mb = round(self.total_bytes / (1024 * 1024), 2)


class SessionInfo(BaseModel):
    """Information sur une session active pour l'API."""
    token: str
    user_id: str
    user_name: str
    ip_client: str
    start_time: datetime
    expires_at: datetime
    remaining_minutes: int
    request_count: int
    total_bytes_mb: float
    dominant_category: Optional[str] = None


class AnomalyAlert(BaseModel):
    """Alerte d'anomalie détectée."""
    user_id: str
    user_name: str
    score_zscore: float = Field(..., description="Score Z-score calculé")
    volume_session_mb: float = Field(..., description="Volume de la session en Mo")
    avg_volume_mb: float = Field(..., description="Volume moyen du groupe en Mo")
    timestamp: datetime = Field(default_factory=datetime.now)
    details: str = Field(..., description="Description détaillée de l'anomalie")


class AlertConfig(BaseModel):
    """Configuration des seuils d'alerte."""
    zscore_threshold: float = Field(3.0, ge=0, le=10, description="Seuil Z-score")
    max_volume_per_session_mb: int = Field(100, ge=0, description="Volume max par session")
    max_session_duration_minutes: int = Field(30, ge=1, description="Durée max de session")
    blocked_categories: List[CategoryEnum] = Field(
        default_factory=list,
        description="Catégories de sites à bloquer"
    )


class HealthStatus(BaseModel):
    """Statut du système pour l'endpoint /health."""
    status: str = Field(..., description="healthy, degraded, unhealthy")
    components: Dict[str, bool] = Field(..., description="État des composants")
    active_sessions: int = Field(..., ge=0)
    dataframe_size: int = Field(..., ge=0)
    queue_size: int = Field(..., ge=0)
    uptime_seconds: float = Field(..., ge=0)
    uptime_formatted: str = Field(..., description="Uptime formaté HH:MM:SS")


class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée pour l'API."""
    error: str = Field(..., description="Message d'erreur")
    detail: Optional[str] = Field(None, description="Détails supplémentaires")
    status_code: int = Field(..., description="Code HTTP")
    timestamp: datetime = Field(default_factory=datetime.now)