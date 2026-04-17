"""
Gestion des sessions utilisateur du proxy.
Vérifie l'authentification de chaque client par son adresse IP.
Interagit avec le module state.py pour la persistence.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import state
from datetime import datetime, timedelta

def is_authenticated(ip_client: str) -> bool:
    """
    Vérifie si un client est authentifié et sa session valide.
    
    Args:
        ip_client: Adresse IP du client (ex: "192.168.1.100")
    
    Returns:
        True si le client a une session valide non expirée, False sinon
    """
    with state.lock:
        if ip_client not in state.sessions:
            return False
        
        session = state.sessions[ip_client]
        
        # Vérifier que la session n'a pas expiré
        if 'expiration' in session:
            if isinstance(session['expiration'], str):
                try:
                    expiration = datetime.fromisoformat(session['expiration'])
                except:
                    return False
            else:
                expiration = session['expiration']
            
            if datetime.now() > expiration:
                # Session expirée, la supprimer
                del state.sessions[ip_client]
                return False
        
        return True


def create_session(ip_client: str, session_data: dict = None, duree_min: int = 30) -> str:
    """
    Crée une nouvelle session pour un client.
    
    Args:
        ip_client: Adresse IP du client
        session_data: Dictionnaire avec les données utilisateur complètes
        duree_min: Durée de la session en minutes (défaut: 30)
    
    Returns:
        ID de session généré
    """
    if session_data:
        # Nouvelle interface avec données complètes
        session_data['ip_client'] = ip_client
        session_data['expires_at'] = (datetime.now()).isoformat()
        session_id = state.ajouter_session(session_data)
        return session_id
    else:
        # Ancienne interface pour compatibilité
        session_id = state.ajouter_session(ip_client, session_data, duree_min)
        return session_id


def logout(ip_client: str) -> bool:
    """
    Supprime la session d'un client.
    
    Args:
        ip_client: Adresse IP du client
    
    Returns:
        True si suppression réussie, False si session inexistante
    """
    with state.lock:
        if ip_client in state.sessions:
            del state.sessions[ip_client]
            state.stats["active_sessions"] = len(state.sessions)
            return True
    return False


def get_session_info(ip_client: str) -> dict:
    """
    Récupère les informations de session d'un client.
    
    Args:
        ip_client: Adresse IP du client
    
    Returns:
        Dictionnaire avec infos de session ou None
    """
    with state.lock:
        return state.sessions.get(ip_client, None)


def record_request(ip_client: str, domaine: str, methode: str, 
                   content_length: int = 0, user_agent: str = "", referer: str = ""):
    """
    Enregistre une requête HTTP pour un client authentifié.
    Crée un événement et le place dans la Queue pour traitement.
    
    Args:
        ip_client: Adresse IP du client
        domaine: Domaine cible (ex: "github.com")
        methode: Méthode HTTP (GET, POST, etc.)
        content_length: Taille du contenu en bytes
        user_agent: En-tête User-Agent
        referer: En-tête Referer
    """
    event = {
        "type": "http_request",
        "timestamp": datetime.now().isoformat(),
        "ip_client": ip_client,
        "domaine": domaine,
        "methode": methode,
        "content_length": content_length,
        "user_agent": user_agent,
        "referer": referer
    }
    
    state.event_queue.put(event)
    
    # Mettre à jour les stats
    with state.lock:
        if ip_client in state.sessions:
            session = state.sessions[ip_client]
            session["nb_requetes"] = session.get("nb_requetes", 0) + 1
            session["volume_bytes"] = session.get("volume_bytes", 0) + content_length
        
        state.stats["total_requests"] += 1
        state.stats["queue_size"] = state.event_queue.qsize()