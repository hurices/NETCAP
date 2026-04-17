"""
Proxy HTTP Intercepteur — Composant Central du Système NETCAP
Port d'écoute: 8080 (TCP)

Responsabilités:
1. Écouter en permanence sur le port 8080
2. Accepter les connexions entrantes dans des threads dédiés
3. Parser les en-têtes HTTP (GET, POST, CONNECT, etc.)
4. Vérifier l'authentification des clients via leur adresse IP
5. Rediriger les clients non authentifiés vers le portail Flask
6. Relayer requêtes/réponses pour les clients authentifiés
7. Enregistrer les événements de navigation dans la Queue partagée
8. Gérer les tunnels CONNECT pour le trafic HTTPS
9. Gérer proprement les ressources et la concurrence

Gestion de la concurrence:
- Chaque client a son propre thread
- Ressources partagées protégées par verrous (Lock)
  - state.sessions (dictionnaire des sessions)
  - state.event_queue (file d'attente des événements)
  - state.stats (statistiques globales)
"""

import socket
import sys
import threading
import urllib.parse
import logging

try:
    from proxy.http_parser import parser_requete_http, construire_reponse_302
    from proxy import session_manager
except ImportError:
    from http_parser import parser_requete_http, construire_reponse_302
    import session_manager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ===========================================================================
# CONSTANTES
# ===========================================================================

BUFFER_SIZE = 4096
HOST = "0.0.0.0"        # Écoute sur toutes les interfaces
PORT = 8080             # Port du proxy
BACKLOG = 5             # Connexions en attente maximum
TIMEOUT_SOCKET = 5      # Timeout pour les opérations socket

# ===========================================================================
# COMPTEURS GLOBAUX (thread-safe)
# ===========================================================================

counter_clients = 0
counter_lock = threading.Lock()


def increment_client_counter():
    """Incrémente le compteur de clients connectés."""
    global counter_clients
    with counter_lock:
        counter_clients += 1
        return counter_clients


def decrement_client_counter():
    """Décrémente le compteur de clients connectés."""
    global counter_clients
    with counter_lock:
        counter_clients -= 1
        return counter_clients


# ===========================================================================
# GESTION DES CLIENTS
# ===========================================================================

def handle_client(connexion: socket.socket, adresse: tuple):
    """
    Traite un client connecté au proxy.
    
    Exécuté dans un thread dédié. Responsable de:
    1. Recevoir la requête HTTP brute
    2. Parser les en-têtes
    3. Vérifier l'authentification via IP
    4. Rediriger si non authentifié, ou relayer la requête
    5. Enregistrer l'événement dans la Queue
    
    Args:
        connexion: Socket client
        adresse: Tuple (ip, port) du client
    """
    ip_client = adresse[0]
    port_client = adresse[1]
    nbr_clients = increment_client_counter()
    
    logger.info(f"✓ Connexion client depuis {ip_client}:{port_client} | Clients actifs: {nbr_clients}")
    
    try:
        connexion.settimeout(TIMEOUT_SOCKET)
        
        # --- 1) Recevoir les données brutes ---
        data = connexion.recv(BUFFER_SIZE)
        
        if not data:
            logger.warning(f"  Aucune donnée reçue de {ip_client}")
            connexion.close()
            return
        
        # --- 2) Parser la requête HTTP ---
        requete = parser_requete_http(data)
        
        if not requete or not requete.est_requete_valide:
            logger.warning(f"  Requête invalide de {ip_client}")
            connexion.close()
            return
        
        logger.info(f"  Requête: {requete}")
        
        # --- 3) Vérifier l'authentification ---
        if not session_manager.is_authenticated(ip_client):
            logger.warning(f"  ✗ {ip_client} non authentifié → redirection portail")
            
            # Construire l'URL de redirection vers le portail Flask
            # avec l'URL demandée comme paramètre
            url_demandee = f"{requete.domaine}{requete.url_path}"
            
            # Créer l'URL de redirection du portail
            redirect_url = f"http://localhost:5000/portail?redirect_url={urllib.parse.quote(url_demandee)}"
            
            response = construire_reponse_302(redirect_url)
            connexion.sendall(response)
            connexion.close()
            return
        
        logger.info(f"  ✓ {ip_client} authentifié")
        
        # --- 4) Relayer la requête selon le type ---
        if requete.methode == "CONNECT":
            # Tunnel HTTPS — relayer sans analyser
            handle_https_tunnel(connexion, ip_client, requete)
        else:
            # Requête HTTP classique — relayer et logger
            handle_http_request(connexion, ip_client, requete)
        
        # --- 5) Enregistrer l'événement ---
        session_manager.record_request(
            ip_client,
            requete.domaine,
            requete.methode,
            requete.content_length,
            requete.user_agent,
            requete.referer
        )
        logger.info(f"  ✓ Événement enregistré pour {requete}")
    
    except socket.timeout:
        logger.warning(f"  Timeout de {ip_client}")
    except Exception as e:
        logger.error(f"  Erreur client {ip_client}: {e}", exc_info=True)
    finally:
        connexion.close()
        nbr_clients = decrement_client_counter()
        logger.info(f"  Déconnexion de {ip_client} | Clients actifs: {nbr_clients}")


def handle_http_request(client_socket: socket.socket, ip_client: str, requete):
    """
    Traite une requête HTTP classique (GET, POST, etc.).
    Relaye la requête vers le serveur de destination et retourne la réponse.
    
    Args:
        client_socket: Socket connectée au client proxy
        ip_client: Adresse IP du client
        requete: Objet RequeteHTTP parsé
    """
    logger.debug(f"  [HTTP] Relayage vers {requete.domaine}:{requete.port}")
    
    try:
        # Créer une connexion vers le serveur de destination
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.settimeout(TIMEOUT_SOCKET)
        
        # Connexion au serveur cible
        server_socket.connect((requete.domaine, requete.port))
        
        # Envoyer la requête complète (headers + body si présent)
        logger.debug(f"  Connexion établie vers {requete.domaine}:{requete.port}")
        
        lignes_headers = [
            f"{requete.methode} {requete.url_path or '/'} HTTP/{requete.version_http}"
        ]

        # Recomposer les headers reçus, en remplaçant les en-têtes proxy spécifiques
        for nom, valeur in requete.en_tetes.items():
            cle = nom.lower()
            if cle in {"proxy-connection", "connection", "keep-alive"}:
                continue
            if cle == "host":
                continue
            lignes_headers.append(f"{nom}: {valeur}")

        lignes_headers.append(f"Host: {requete.host_header}")
        lignes_headers.append("Connection: close")

        requete_brute = "\r\n".join(lignes_headers).encode("utf-8") + b"\r\n\r\n" + (requete.body or b"")
        server_socket.sendall(requete_brute)
        
        # Recevoir la réponse du serveur
        response_data = b""
        while True:
            chunk = server_socket.recv(BUFFER_SIZE)
            if not chunk:
                break
            response_data += chunk
        
        # Envoyer la réponse au client
        client_socket.sendall(response_data)
        
        logger.info(f"  ✓ Requête relayée avec succès | {len(response_data)} bytes")
        server_socket.close()
    
    except socket.timeout:
        logger.warning(f"  Timeout vers {requete.domaine}")
        error_response = (
            "HTTP/1.1 504 Gateway Timeout\r\n"
            "Content-Type: text/plain\r\n\r\n"
            "Le serveur cible ne répond pas (timeout)."
        ).encode()
        client_socket.sendall(error_response)
    
    except (socket.gaierror, ConnectionRefusedError) as e:
        logger.error(f"  Impossible de se connecter à {requete.domaine}: {e}")
        error_response = (
            "HTTP/1.1 503 Service Unavailable\r\n"
            "Content-Type: text/plain\r\n\r\n"
            f"Impossible de se connecter à {requete.domaine}."
        ).encode()
        client_socket.sendall(error_response)
    
    except Exception as e:
        logger.error(f"  Erreur relayage HTTP: {e}")


def handle_https_tunnel(client_socket: socket.socket, ip_client: str, requete):
    """
    Traite un tunnel HTTPS (requête CONNECT).
    Relaye le trafic crypté sans l'analyser, selon le modèle des proxys réels.
    
    Note: Le proxy ne peut pas déchiffrer le trafic HTTPS, il se contente
    de relayer les bytes bruts. C'est le comportement attendu et sécurisé.
    
    Args:
        client_socket: Socket connectée au client
        ip_client: Adresse IP du client
        requete: Objet RequeteHTTP avec CONNECT
    """
    logger.debug(f"  [HTTPS] Établissement tunnel CONNECT vers {requete.domaine}:{requete.port}")
    
    try:
        # Créer une connexion vers le serveur cible (ex: https://github.com)
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.settimeout(TIMEOUT_SOCKET)
        
        server_socket.connect((requete.domaine, requete.port))
        
        # Envoyer la réponse 200 Connection Established au client
        # Cela signifie que le tunnel est prêt
        tunnel_response = (
            "HTTP/1.1 200 Connection Established\r\n"
            "Connection: close\r\n\r\n"
        ).encode()
        client_socket.sendall(tunnel_response)
        
        logger.info(f"  ✓ Tunnel HTTPS établi vers {requete.domaine}:{requete.port}")
        
        # Relayer le trafic bidirectionnel (client ↔ serveur)
        # Ceci se fait généralement avec select() ou threading
        # Implémentation simplifiée: relayer dans une direction puis l'autre
        
        # Dans une vraie implémentation, il faudrait utiliser select()
        # ou des threads pour relayer bidirectionnel simultanément
        relay_tunnel_traffic(client_socket, server_socket)
        
        logger.info(f"  ✓ Tunnel HTTPS fermé pour {requete.domaine}")
        server_socket.close()
    
    except socket.timeout:
        logger.warning(f"  Timeout HTTPS vers {requete.domaine}")
    except (socket.gaierror, ConnectionRefusedError) as e:
        logger.error(f"  Impossible de se connecter à {requete.domaine}: {e}")
        error_response = (
            "HTTP/1.1 503 Service Unavailable\r\n\r\n"
        ).encode()
        client_socket.sendall(error_response)
    except Exception as e:
        logger.error(f"  Erreur tunnel HTTPS: {e}")


def relay_tunnel_traffic(client_sock: socket.socket, server_sock: socket.socket):
    """
    Relaye le trafic bidirectionnel entre client et serveur pour HTTPS.
    
    Implémentation simplifiée: lit du client, relaye au serveur, vice-versa.
    Une vraie implémentation utiliserait select() ou des threads séparés
    pour la communication bidirectionnelle simultanée.
    
    Args:
        client_sock: Socket client
        server_sock: Socket serveur
    """
    try:
        # Relayer client → serveur
        while True:
            data = client_sock.recv(BUFFER_SIZE)
            if not data:
                break
            server_sock.sendall(data)
        
        # Relayer serveur → client
        while True:
            data = server_sock.recv(BUFFER_SIZE)
            if not data:
                break
            client_sock.sendall(data)
    
    except (socket.timeout, BrokenPipeError):
        pass  # Fermeture normale du tunnel
    except Exception as e:
        logger.debug(f"Erreur relayage tunnel: {e}")


# ===========================================================================
# SERVEUR PROXY
# ===========================================================================

def create_server():
    """
    Crée et démarre le serveur proxy TCP.
    
    - Crée un socket TCP serveur
    - Lie le socket au port 8080
    - Accepte les connexions entrantes
    - Crée un thread pour chaque client
    - Exécution infinie (jusqu'à Ctrl+C)
    """
    logger.info("=" * 70)
    logger.info("DÉMARRAGE DU PROXY HTTP NETCAP")
    logger.info("=" * 70)
    logger.info(f"Écoute sur {HOST}:{PORT}")
    logger.info(f"Buffer size: {BUFFER_SIZE} bytes")
    logger.info(f"Timeout socket: {TIMEOUT_SOCKET}s")
    logger.info("=" * 70)
    
    # Créer le socket serveur
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # Lier le socket à l'adresse et au port
        server_socket.bind((HOST, PORT))
        logger.info(f"✓ Socket lié à {HOST}:{PORT}")
    except socket.error as e:
        logger.error(f"✗ Erreur liaison socket: {e}")
        sys.exit(1)
    
    try:
        # Mettre le socket en mode écoute
        server_socket.listen(BACKLOG)
        logger.info(f"✓ Serveur en écoute (backlog={BACKLOG})")
        logger.info("En attente de connexions client...")
        logger.info("-" * 70)
        
        # Boucle infinie d'acceptation des connexions
        while True:
            try:
                # Accepter une connexion
                connexion, adresse = server_socket.accept()
                
                # Créer un thread pour traiter ce client
                thread = threading.Thread(
                    target=handle_client,
                    args=(connexion, adresse),
                    daemon=False
                )
                thread.start()
            
            except KeyboardInterrupt:
                logger.info("\n✓ Arrêt du serveur demandé par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"Erreur acception connexion: {e}")
    
    except KeyboardInterrupt:
        logger.info("\n✓ Arrêt du serveur")
    except Exception as e:
        logger.error(f"Erreur serveur fatal: {e}", exc_info=True)
    finally:
        server_socket.close()
        logger.info("✓ Socket serveur fermé")
        logger.info("=" * 70)
        logger.info("FIN DU PROXY")
        logger.info("=" * 70)


# ===========================================================================
# POINT D'ENTRÉE
# ===========================================================================

if __name__ == "__main__":
    create_server()
