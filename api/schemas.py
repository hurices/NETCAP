from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class CategoryEnum(str, Enum):
    """Types de catégories de sites web."""
    SOCIAL = "Social"
    STREAMING = "Streaming"
    NEWS = "News"
    SHOPPING = "Shopping"
    DEVELOPMENT = "Development"
    SEARCH = "Search"
    PRODUCTIVITY = "Productivity"
    EMAIL = "Email"
    EDUCATION = "Education"
    GAMING = "Gaming"
    OTHER = "Autre"
    ADULT = "Adult"
    MALWARE = "Malware"
    GAMBLING = "Gambling"


class PeriodeAnalyse(str, Enum):
    """Périodes de temps pour les statistiques."""
    CINQ_MIN = "5m"
    UNE_HEURE = "1h"
    QUATRE_HEURES = "4h"
    VINGT_QUATRE_HEURES = "24h"


class SessionActive(BaseModel):
    """Représente une session active dans le système."""
    ip_client: str
    user_id: str
    session_id: str
    debut: datetime
    expiration: datetime
    nb_requetes: int
    volume_bytes: int
    categorie_dominante: Optional[str] = "Autre"


class SessionDetail(SessionActive):
    """Détails complets d'une session avec historique récent."""
    derniers_evenements: List[Dict] = []


class EvenementNavigation(BaseModel):
    """Représente un événement de navigation capturé par le proxy."""
    timestamp: datetime
    ip_client: str
    user_id: str
    session_id: str
    methode: str
    domaine: str
    categorie: str
    taille_bytes: int
    duree_ms: int
    statut_http: int
    est_https: bool


class TopDomaine(BaseModel):
    """Représente un domaine fréquent."""
    domaine: str
    count: int


class MetriqueTrafic(BaseModel):
    """Contient les métriques globales de trafic pour une période."""
    periode: str
    debut_periode: datetime
    fin_periode: datetime
    total_requetes: int
    total_bytes: int
    requetes_par_minute: float
    taux_erreur_pct: float
    top_domaines: List[TopDomaine]
    repartition_categories: Dict[str, int]
    utilisateurs_actifs: int


class StatUtilisateur(BaseModel):
    """Statistiques par utilisateur."""
    user_id: str
    total_requetes: int
    total_bytes: int
    derniere_activite: datetime
    top_categorie: str


class AlerteAnomalie(BaseModel):
    """Représente une alerte générée lors d'un comportement anormal."""
    alerte_id: str
    user_id: str
    ip_client: str
    score_zscore: float
    volume_session: int
    volume_moyen_groupe: float
    timestamp_detection: datetime
    details: str
    acquittee: bool = False


class ConfigSeuils(BaseModel):
    """Configuration dynamique des seuils du système."""
    model_config = ConfigDict(protected_namespaces=())
    zscore_seuil: float
    volume_max_session_mb: int
    duree_session_max_min: int
    categories_bloquees: List[str]
    requetes_par_minute_max: int


class ParametresExport(BaseModel):
    """Paramètres pour l'export CSV."""
    debut: datetime
    fin: datetime
    colonnes: Optional[List[str]] = None