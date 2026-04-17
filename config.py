

"""
Fichier de configuration global du projet NetCapt.
Toutes les constantes du système doivent être définies ici.
Cela permet d'éviter les valeurs en dur dans le code.
"""

# Ports des différents services
PROXY_PORT = 8080
FLASK_PORT = 5000
FASTAPI_PORT = 8000

# Sécurité API
ADMIN_TOKEN_HEADER = "X-Admin-Token"
ADMIN_TOKEN_SECRET = "netcapt-secret-2026"
ADMIN_TOKEN = ADMIN_TOKEN_SECRET # Alias pour simplification

# URLs par défaut
API_URL = f"http://localhost:{FASTAPI_PORT}"

# Durée de vie des sessions utilisateur (en minutes)
SESSION_DURATION_MIN = 30

# Taille de la fenêtre d'analyse (en heures)
WINDOW_SIZE_HOURS = 4

# Seuils de détection d'anomalies (Valeurs par défaut)
ANOMALIE_ZSCORE_SEUIL = 3.0
ANOMALIE_VOLUME_MAX_SESSION_MB = 100
ANOMALIE_DUREE_SESSION_MAX_MIN = 60
ANOMALIE_REQUETES_PAR_MINUTE_MAX = 50
ANOMALIE_MIN_SAMPLES = 10

# Configuration du pipeline
CONSUMER_SLEEP_SECONDS = 0.5
MAX_DATAFRAME_SIZE = 50000

# Catégories de sites bloquées par défaut
CATEGORIES_BLOQUEES = ["Adult", "Malware", "Gambling"]

# Règles de catégorisation initiale
CATEGORIZATION_RULES = {
    "google.com": "Search",
    "facebook.com": "Social",
    "youtube.com": "Streaming",
    "netflix.com": "Streaming",
    "github.com": "Development",
    "stackoverflow.com": "Development",
    "amazon.com": "Shopping",
    "lemonde.fr": "News"
}

# Intervalle de rafraîchissement du dashboard (ms)
REFRESH_INTERVAL_MS = 5000

# Archivage
ARCHIVE_PATH = "data/archives/"
LOG_FILE = "logs/netcapt.log"