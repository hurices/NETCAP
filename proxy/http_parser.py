"""
Responsabilité unique : extraire les métadonnées d'une requête HTTP brute
reçue par le proxy. Ne fait aucun I/O réseau.

Supporte :
  - Requêtes HTTP classiques  : GET http://example.com/path HTTP/1.1
  - Tunnels HTTPS (CONNECT)   : CONNECT github.com:443 HTTP/1.1
  - Requêtes avec path relatif: GET /path HTTP/1.1  (Host: obligatoire)

Usage :
    from proxy.http_parser import parser_requete_http, RequeteHTTP
    requete = parser_requete_http(donnees_brutes)
    if requete:
        print(requete.domaine, requete.methode)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

logger = logging.getLogger(__name__)

# ===========================================================================
# CONSTANTES DE PARSING
# ===========================================================================

# Méthodes HTTP reconnues par le proxy
METHODES_HTTP = frozenset({
    "GET", "POST", "PUT", "PATCH", "DELETE",
    "HEAD", "OPTIONS", "CONNECT", "TRACE",
})

# Regex pour valider une adresse IP v4
_RE_IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# Regex pour extraire le domaine et le port depuis une ligne CONNECT
# Exemple : "CONNECT github.com:443 HTTP/1.1" → ('github.com', '443')
_RE_CONNECT = re.compile(r"^CONNECT\s+([^:\s]+)(?::(\d+))?\s+HTTP/", re.IGNORECASE)

# Regex pour extraire la version HTTP
_RE_VERSION = re.compile(r"HTTP/(\d+\.\d+)", re.IGNORECASE)


# ===========================================================================
# STRUCTURE DE RÉSULTAT
# ===========================================================================

@dataclass
class RequeteHTTP:
    """
    Métadonnées extraites d'une requête HTTP brute.
    Toutes les valeurs sont normalisées (minuscules pour domaine, etc.).
    """

    methode: str                        # GET, POST, CONNECT, ...
    domaine: str                        # github.com (sans port)
    port: int                           # 80 (HTTP) ou 443 (HTTPS/CONNECT)
    url_path: str                       # /questions/123 ou "" pour CONNECT
    version_http: str                   # "1.1", "2.0", ...
    est_https: bool                     # True si méthode CONNECT
    host_header: str                    # Valeur brute de l'en-tête Host
    user_agent: str                     # User-Agent ou "" si absent
    content_length: int                 # Valeur de Content-Length (0 si absent)
    referer: str                        # Valeur de Referer ou ""
    body: bytes = b""                 # Corps de la requête, si présent
    en_tetes: dict[str, str] = field(default_factory=dict)  # Tous les en-têtes

    @property
    def domaine_normalise(self) -> str:
        """Domaine en minuscules, sans port, sans www. optionnel."""
        return self.domaine.lower().strip()

    @property
    def est_requete_valide(self) -> bool:
        """True si le domaine est non vide et la méthode reconnue."""
        return bool(self.domaine) and self.methode in METHODES_HTTP

    def __str__(self) -> str:
        proto = "HTTPS" if self.est_https else "HTTP"
        return f"[{proto}] {self.methode} {self.domaine}{self.url_path}"


# ===========================================================================
# FONCTIONS PUBLIQUES
# ===========================================================================

def parser_requete_http(donnees_brutes: bytes) -> RequeteHTTP | None:
    """
    Parse les données brutes reçues sur le socket et extrait les métadonnées HTTP.

    Args:
        donnees_brutes: Bytes bruts lus depuis le socket client. Peuvent
                        contenir uniquement les en-têtes (body exclu).

    Returns:
        RequeteHTTP si le parsing réussit, None si les données sont invalides
        ou incomplètes (moins de 2 lignes, méthode inconnue, domaine absent).

    Exceptions :
        Aucune — les erreurs sont loguées et None est retourné.
    """
    if not donnees_brutes:
        return None

    # Séparer les en-têtes du corps en bytes
    if b"\r\n\r\n" in donnees_brutes:
        section_entetes, corps = donnees_brutes.split(b"\r\n\r\n", 1)
        separateur = b"\r\n"
    elif b"\n\n" in donnees_brutes:
        section_entetes, corps = donnees_brutes.split(b"\n\n", 1)
        separateur = b"\n"
    else:
        # Pas de séparation trouvée : la requête est incomplète ou invalide
        logger.debug("Aucun séparateur de headers trouvé")
        return None

    # Décoder uniquement la partie en-têtes (fallback latin-1 pour tolérance)
    try:
        texte_entetes = section_entetes.decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug("Échec décodage en-têtes UTF-8 : %s", e)
        return None

    lignes = texte_entetes.split(separateur.decode())
    if len(lignes) < 1:
        logger.debug("Requête trop courte — impossible à parser")
        return None

    # --- Parser la ligne de requête (première ligne) ---
    requete_line = lignes[0].strip()
    methode, domaine, port, url_path, version, est_https = _parser_ligne_requete(requete_line)

    if methode is None:
        logger.debug("Ligne de requête invalide : %r", requete_line[:100])
        return None

    # --- Parser les en-têtes (lignes suivantes) ---
    en_tetes = _parser_en_tetes(lignes[1:])

    # Compléter le domaine depuis Host si absent (requêtes avec path relatif)
    if not domaine and "host" in en_tetes:
        domaine, port = _extraire_domaine_port(en_tetes["host"], port)

    if not domaine:
        logger.debug("Domaine introuvable dans la requête : %r", requete_line[:100])
        return None

    # Extraire les champs spécifiques
    user_agent = en_tetes.get("user-agent", "")
    referer = en_tetes.get("referer", "")
    content_length_str = en_tetes.get("content-length", "0")
    host_header = en_tetes.get("host", domaine)

    try:
        content_length = int(content_length_str)
    except ValueError:
        content_length = 0

    return RequeteHTTP(
        methode=methode,
        domaine=domaine.lower(),
        port=port,
        url_path=url_path,
        version_http=version,
        est_https=est_https,
        host_header=host_header,
        user_agent=user_agent,
        content_length=content_length,
        referer=referer,
        body=corps,
        en_tetes=en_tetes,
    )


def construire_reponse_302(url_redirection: str) -> bytes:
    """
    Construit une réponse HTTP 302 Found pour rediriger le client vers le portail.

    Args:
        url_redirection: URL complète du portail Flask avec redirect_url encodée.

    Returns:
        Bytes de la réponse HTTP 302 prête à être envoyée sur le socket.

    Exemple :
        >>> url = "http://127.0.0.1:5000/portail?redirect_url=http%3A//example.com"
        >>> reponse = construire_reponse_302(url)
    """
    corps = (
        "<html><body>"
        f"<p>Authentification requise. "
        f'<a href="{url_redirection}">Cliquez ici</a> pour vous connecter.</p>'
        "</body></html>"
    ).encode("utf-8")

    entetes = (
        "HTTP/1.1 302 Found\r\n"
        f"Location: {url_redirection}\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(corps)}\r\n"
        "Connection: close\r\n"
        "Cache-Control: no-cache, no-store, must-revalidate\r\n"
        "\r\n"
    ).encode("utf-8")

    return entetes + corps


def encoder_url(url: str) -> str:
    """
    Encode minimalement une URL pour l'utiliser comme paramètre de query string.
    Remplace les caractères spéciaux les plus courants.

    Args:
        url: URL brute (ex: "http://github.com/path?q=1")

    Returns:
        URL encodée (ex: "http%3A//github.com/path%3Fq%3D1")
    """
    # Encodage minimaliste compatible avec urllib.parse.quote
    import urllib.parse
    return urllib.parse.quote(url, safe="")


# ===========================================================================
# FONCTIONS PRIVÉES
# ===========================================================================

def _parser_ligne_requete(
    ligne: str,
) -> tuple[str | None, str, int, str, str, bool]:
    """
    Parse la première ligne d'une requête HTTP.

    Args:
        ligne: Ex. "GET http://example.com/path HTTP/1.1"
               Ex. "CONNECT github.com:443 HTTP/1.1"
               Ex. "GET /path HTTP/1.1"

    Returns:
        Tuple (methode, domaine, port, url_path, version_http, est_https).
        methode est None si la ligne est invalide.
    """
    parties = ligne.split()
    if len(parties) < 2:
        return None, "", 80, "/", "1.1", False

    methode = parties[0].upper()
    if methode not in METHODES_HTTP:
        return None, "", 80, "/", "1.1", False

    cible = parties[1]
    version = "1.1"
    if len(parties) >= 3:
        match_version = _RE_VERSION.search(parties[2])
        if match_version:
            version = match_version.group(1)

    # Cas CONNECT (tunnel HTTPS)
    if methode == "CONNECT":
        match = _RE_CONNECT.match(ligne)
        if match:
            domaine = match.group(1)
            port_str = match.group(2)
            port = int(port_str) if port_str else 443
        else:
            # Fallback : parser manuellement
            domaine, port = _extraire_domaine_port(cible, 443)
        return methode, domaine.lower(), port, "", version, True

    # Cas URL absolue : GET http://example.com/path HTTP/1.1
    if cible.startswith("http://") or cible.startswith("https://"):
        import urllib.parse
        parsed = urllib.parse.urlparse(cible)
        domaine = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        url_path = parsed.path or "/"
        if parsed.query:
            url_path += "?" + parsed.query
        est_https = parsed.scheme == "https"
        return methode, domaine.lower(), port, url_path, version, est_https

    # Cas path relatif : GET /path HTTP/1.1  (Host header sera utilisé)
    url_path = cible if cible.startswith("/") else "/"
    return methode, "", 80, url_path, version, False


def _parser_en_tetes(lignes: list[str]) -> dict[str, str]:
    """
    Extrait les en-têtes HTTP depuis les lignes après la ligne de requête.
    Les clés sont normalisées en minuscules.

    Args:
        lignes: Lignes des en-têtes (sans la première ligne de requête).

    Returns:
        Dictionnaire {nom_en_tete_lowercase: valeur}.
    """
    en_tetes: dict[str, str] = {}
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne:
            break  # Fin des en-têtes
        if ":" in ligne:
            nom, _, valeur = ligne.partition(":")
            # Tronquer les valeurs trop longues (sécurité)
            en_tetes[nom.strip().lower()] = valeur.strip()[:512]
    return en_tetes


def _extraire_domaine_port(host_str: str, port_defaut: int = 80) -> tuple[str, int]:
    """
    Extrait le domaine et le port depuis un header Host ou une cible CONNECT.

    Args:
        host_str: Ex. "github.com", "github.com:443", "[::1]:8080"
        port_defaut: Port à utiliser si aucun port n'est spécifié.

    Returns:
        Tuple (domaine, port).
    """
    host_str = host_str.strip()

    # Adresse IPv6 entre crochets : [::1]:8080
    if host_str.startswith("["):
        bracket_end = host_str.find("]")
        if bracket_end != -1:
            domaine = host_str[1:bracket_end]
            reste = host_str[bracket_end + 1:]
            if reste.startswith(":"):
                try:
                    return domaine, int(reste[1:])
                except ValueError:
                    pass
            return domaine, port_defaut

    # Domaine ou IP avec port éventuel
    if ":" in host_str:
        parties = host_str.rsplit(":", 1)
        try:
            port = int(parties[1])
            return parties[0].lower(), port
        except ValueError:
            pass

    return host_str.lower(), port_defaut