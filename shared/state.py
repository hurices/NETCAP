from queue import Queue
from threading import Lock
from datetime import datetime, timedelta
import uuid
import time

"""
Ce module centralise les structures de données partagées
et la gestion des sessions utilisateur.

Il est utilisé par plusieurs composants :
- proxy
- portail
- API
- pipeline d'analyse

Toutes les opérations sur les sessions sont protégées
par un verrou pour éviter les problèmes de concurrence.
"""

# File d'attente des événements de navigation
event_queue = Queue()

# Dictionnaire des sessions actives
# clé : ip_client
# valeur : informations de session
sessions = {}

# Dictionnaire des alertes
alerts = {}

# Dictionnaire des statistiques
stats = {
    "active_sessions": 0,
    "queue_size": 0,
    "total_requests": 0,
    "uptime_seconds": 0,
    "start_time": datetime.now()
}

# Verrou pour sécuriser les accès concurrents
lock = Lock()
_running = True

def is_running():
    return _running

def stop_system():
    global _running
    _running = False


def ajouter_session(ip_client, user_id=None, duree_min=30):
    """
    Crée une nouvelle session pour un utilisateur.
    Supporte la signature classique du Sprint 2 et la signature par dictionnaire.
    """
    with lock:
        session_id = str(uuid.uuid4())
        
        # Si ip_client est un dictionnaire (cas de l'injection directe de données complexes)
        if isinstance(ip_client, dict) and 'ip_client' in ip_client:
            session_data = ip_client
            target_ip = session_data['ip_client']
            duration = duree_min
            # Fusionner les données
            session_record = session_data.copy()
            session_record.setdefault('session_id', session_id)
            session_record.setdefault('debut', datetime.now())
            session_record['expiration'] = datetime.now() + timedelta(minutes=duration)
            sessions[target_ip] = session_record
        else:
            # Signature classique
            expiration = datetime.now() + timedelta(minutes=duree_min)
            sessions[ip_client] = {
                "session_id": session_id,
                "ip_client": ip_client,
                "user_id": user_id,
                "debut": datetime.now(),
                "expiration": expiration,
                "nb_requetes": 0,
                "volume_bytes": 0
            }
        
        stats["active_sessions"] = len(sessions)
        return session_id


def obtenir_session(ip_client: str):
    """
    Récupère une session à partir de l'adresse IP.
    """
    with lock:
        session = sessions.get(ip_client)
        if session:
            return session.copy()  # Retourner une copie
        return None


def get_session(ip_client: str):
    """
    Alias pour obtenir_session pour compatibilité.
    """
    return obtenir_session(ip_client)


def revoquer_session(ip_client: str, reason: str = ""):
    """
    Révoque une session existante.
    
    :param ip_client: adresse IP du client
    :param reason: raison de la révocation
    :return: True si la session a été révoquée, False sinon
    """
    with lock:
        if ip_client in sessions:
            del sessions[ip_client]
            stats["active_sessions"] = len(sessions)
            return True
        return False


def supprimer_session(ip_client: str):
    """
    Supprime une session existante. Alias pour compatibilité.
    """
    revoquer_session(ip_client)


def session_est_valide(ip_client: str):
    """
    Vérifie si une session existe et n'est pas expirée.
    """
    with lock:
        session = sessions.get(ip_client)
        
        if not session:
            return False
        
        # Vérifier l'expiration
        expiration = session.get('expiration')
        if not expiration:
            return False
        
        if expiration < datetime.now():
            del sessions[ip_client]
            stats["active_sessions"] = len(sessions)
            return False
        
        return True


def session_valide(ip_client: str):
    """
    Alias pour session_est_valide pour compatibilité.
    """
    return session_est_valide(ip_client)


def lister_sessions_actives():
    """
    Liste toutes les sessions actives (non expirées).
    
    :return: liste des sessions actives
    """
    with lock:
        # Purger d'abord les sessions expirées
        expired_ips = []
        for ip in list(sessions.keys()):
            session = sessions[ip]
            expiration = session.get('expiration')
            if expiration and expiration < datetime.now():
                expired_ips.append(ip)
        
        for ip in expired_ips:
            if ip in sessions:
                del sessions[ip]
        
        stats["active_sessions"] = len(sessions)
        return list(sessions.values())


def purger_sessions_expirees():
    """
    Supprime toutes les sessions expirées.
    
    :return: nombre de sessions supprimées
    """
    with lock:
        expired_ips = []
        for ip, session in list(sessions.items()):
            expiration = session.get('expiration')
            if expiration and expiration < datetime.now():
                expired_ips.append(ip)
        
        for ip in expired_ips:
            if ip in sessions:
                del sessions[ip]
        
        stats["active_sessions"] = len(sessions)
        return len(expired_ips)


def ajouter_evenement(event: dict):
    """
    Ajoute un événement à la file d'événements.
    
    :param event: dictionnaire représentant l'événement
    :return: True si ajouté avec succès
    """
    try:
        event_queue.put(event, block=False)
        with lock:
            stats["queue_size"] = event_queue.qsize()
            stats["total_requests"] += 1
        return True
    except:
        return False


def obtenir_evenement(timeout=None):
    """
    Récupère un événement de la file.
    
    :param timeout: délai d'attente en secondes
    :return: événement ou None
    """
    try:
        event = event_queue.get(timeout=timeout)
        with lock:
            stats["queue_size"] = event_queue.qsize()
        return event
    except:
        return None


def taille_queue():
    """
    Retourne la taille actuelle de la file d'événements.
    """
    return event_queue.qsize()


def ajouter_alerte(alerte: dict):
    """
    Ajoute une alerte au système.
    
    :param alerte: dictionnaire représentant l'alerte
    """
    with lock:
        alerte_id = alerte.get('alerte_id', str(uuid.uuid4()))
        alerte['alerte_id'] = alerte_id
        alerte['created_at'] = datetime.now().isoformat()
        if 'acquittee' not in alerte:
            alerte['acquittee'] = False
        alerts[alerte_id] = alerte


def lister_alertes():
    """
    Liste toutes les alertes.
    
    :return: liste des alertes
    """
    with lock:
        return list(alerts.values())


def acquitter_alerte(alerte_id: str):
    """
    Marque une alerte comme acquittée.
    
    :param alerte_id: identifiant de l'alerte
    :return: True si acquittée avec succès
    """
    with lock:
        if alerte_id in alerts:
            alerts[alerte_id]['acquittee'] = True
            alerts[alerte_id]['acquitted_at'] = datetime.now().isoformat()
            return True
        return False


def get_stats():
    """
    Retourne les statistiques du système.
    
    :return: dictionnaire des statistiques
    """
    with lock:
        current_stats = stats.copy()
        if 'start_time' in current_stats:
            uptime = datetime.now() - current_stats.pop('start_time')
            current_stats['uptime_seconds'] = int(uptime.total_seconds())
        current_stats['active_sessions'] = len(sessions)
        current_stats['queue_size'] = event_queue.qsize()
        return current_stats


def reset_stats():
    """
    Réinitialise les statistiques et nettoie les queues.
    """
    with lock:
        global stats
        stats = {
            "active_sessions": 0,
            "queue_size": 0,
            "total_requests": 0,
            "uptime_seconds": 0,
            "start_time": datetime.now()
        }
        # Vider les queues et les stocks
        while not event_queue.empty():
            try:
                event_queue.get_nowait()
            except:
                break
        alerts.clear()
        # Note: ne pas vider les sessions par défaut