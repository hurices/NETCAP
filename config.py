"""Paramètres globaux du système NetCapt.
Tous les composants importent cette configuration.
"""

import os
from typing import List, Dict


class Config:
    """Configuration centralisée du système"""

    # ===== Proxy =====
    PROXY_HOST: str = "0.0.0.0"
    PROXY_PORT: int = 8080
    PROXY_MAX_CLIENTS: int = 10
    PROXY_BUFFER_SIZE: int = 8192
    PROXY_TIMEOUT: int = 30

    # ===== Portail Flask =====
    FLASK_HOST: str = "0.0.0.0"
    FLASK_PORT: int = 5000
    FLASK_DEBUG: bool = True
    FLASK_SECRET_KEY: str = "netcapt-secret-key-change-in-production"

    # ===== API FastAPI =====
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "NetCapt API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API d'administration du portail captif"

    # ===== Sessions =====
    SESSION_DURATION_MINUTES: int = 30
    SESSION_CLEANUP_INTERVAL_SECONDS: int = 60

    # ===== Pipeline d'analyse =====
    DATAFRAME_WINDOW_HOURS: int = 4
    QUEUE_MAX_SIZE: int = 10000
    CONSUMER_SLEEP_SECONDS: float = 0.1
    ARCHIVE_CSV_PATH: str = "archives/"

    # ===== Catégorisation =====
    CATEGORIZATION_RULES: Dict[str, str] = {
        # Réseaux sociaux
        "facebook.com": "Réseaux sociaux",
        "instagram.com": "Réseaux sociaux",
        "twitter.com": "Réseaux sociaux",
        "x.com": "Réseaux sociaux",
        "linkedin.com": "Réseaux sociaux",
        "tiktok.com": "Réseaux sociaux",
        "snapchat.com": "Réseaux sociaux",
        "pinterest.com": "Réseaux sociaux",
        "reddit.com": "Réseaux sociaux",
        # Streaming vidéo
        "youtube.com": "Streaming vidéo",
        "netflix.com": "Streaming vidéo",
        "twitch.tv": "Streaming vidéo",
        "dailymotion.com": "Streaming vidéo",
        "vimeo.com": "Streaming vidéo",
        "disneyplus.com": "Streaming vidéo",
        "primevideo.com": "Streaming vidéo",
        # Streaming audio
        "spotify.com": "Streaming audio",
        "deezer.com": "Streaming audio",
        "soundcloud.com": "Streaming audio",
        "apple.com/music": "Streaming audio",
        # Développement
        "github.com": "Développement",
        "stackoverflow.com": "Développement",
        "gitlab.com": "Développement",
        "bitbucket.org": "Développement",
        "docs.python.org": "Développement",
        "npmjs.com": "Développement",
        "pypi.org": "Développement",
        # Actualités
        "lemonde.fr": "Actualités",
        "lefigaro.fr": "Actualités",
        "liberation.fr": "Actualités",
        "bbc.com": "Actualités",
        "bbc.co.uk": "Actualités",
        "cnn.com": "Actualités",
        "reuters.com": "Actualités",
        "20minutes.fr": "Actualités",
        # Moteurs de recherche
        "google.com": "Moteurs de recherche",
        "bing.com": "Moteurs de recherche",
        "duckduckgo.com": "Moteurs de recherche",
        "qwant.com": "Moteurs de recherche",
        "yahoo.com": "Moteurs de recherche",
        "ecosia.org": "Moteurs de recherche",
        # Messagerie
        "gmail.com": "Messagerie",
        "outlook.com": "Messagerie",
        "yahoo.com/mail": "Messagerie",
        "protonmail.com": "Messagerie",
        "mail.google.com": "Messagerie",
        # E-commerce
        "amazon.fr": "E-commerce",
        "amazon.com": "E-commerce",
        "ebay.fr": "E-commerce",
        "ebay.com": "E-commerce",
        "cdiscount.com": "E-commerce",
        "leboncoin.fr": "E-commerce",
        "aliexpress.com": "E-commerce",
        "fnac.com": "E-commerce",
        "darty.com": "E-commerce",
        # Éducation
        "wikipedia.org": "Éducation",
        "coursera.org": "Éducation",
        "udemy.com": "Éducation",
        "openclassrooms.com": "Éducation",
        "khanacademy.org": "Éducation",
        "moodle.org": "Éducation",
    }

    # ===== Détection d'anomalies =====
    ANOMALY_ZSCORE_THRESHOLD: float = 3.0
    ANOMALY_VOLUME_MAX_MB: int = 100
    ANOMALY_CHECK_INTERVAL_SECONDS: int = 30

    # ===== Dashboard =====
    DASHBOARD_REFRESH_SECONDS: int = 5
    DASHBOARD_TITLE: str = "NetCapt - Dashboard Administrateur"
    DASHBOARD_WIDTH: int = 1200
    DASHBOARD_HEIGHT: int = 800

    # ===== RGPD =====
    DATA_RETENTION_DAYS: int = 7
    CONSENT_REQUIRED: bool = True

    # ===== Catégories bloquées =====
    BLOCKED_CATEGORIES: List[str] = []

    # ===== Logging =====
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "netcapt.log"

    @classmethod
    def from_env(cls):
        """Charge la configuration depuis les variables d'environnement"""
        cls.PROXY_PORT = int(os.getenv("NETCAPT_PROXY_PORT", cls.PROXY_PORT))
        cls.FLASK_PORT = int(os.getenv("NETCAPT_FLASK_PORT", cls.FLASK_PORT))
        cls.API_PORT = int(os.getenv("NETCAPT_API_PORT", cls.API_PORT))
        cls.SESSION_DURATION_MINUTES = int(os.getenv("NETCAPT_SESSION_DURATION", cls.SESSION_DURATION_MINUTES))
        cls.ANOMALY_ZSCORE_THRESHOLD = float(os.getenv("NETCAPT_ANOMALY_ZSCORE", cls.ANOMALY_ZSCORE_THRESHOLD))
        return cls


# Instance unique utilisée par tous les composants
config = Config()
config.from_env()