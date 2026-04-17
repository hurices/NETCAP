"""
Portail d'Authentification Flask — Composant Interface Utilisateur NETCAP
Port d'écoute: 5000 (HTTP)

Responsabilités:
1. Interface utilisateur pour l'authentification des clients
2. Collecte du consentement RGPD explicite
3. Gestion des sessions utilisateur avec durée configurable
4. Communication avec le proxy via session_manager
5. Redirections vers les URLs originales après authentification

Routes implémentées:
- GET /portail : Page de connexion avec formulaire et CGU
- POST /portail/auth : Validation formulaire, création session
- GET /portail/status : Statut de session en JSON
- GET /portail/logout : Invalidation de session
- GET /portail/cgu : Page des Conditions Générales d'Utilisation

Sécurité:
- Validation côté serveur de tous les champs
- Vérification explicite du consentement CGU
- Sessions avec expiration automatique
- Protection contre les attaques CSRF (via Flask-WTF si nécessaire)
"""

import sys
import os
import re
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for, jsonify, flash, session as flask_session

# 🔧 Configuration des chemins pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "proxy")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shared")))

import session_manager
from shared import state

# ===========================================================================
# CONFIGURATION
# ===========================================================================

app = Flask(__name__)
app.secret_key = "netcap_portail_secret_key_2026"  # À changer en production

# Configuration des sessions
SESSION_DURATION_MINUTES = 30  # Durée par défaut des sessions

# Regex pour validation email
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# ===========================================================================
# FONCTIONS UTILITAIRES
# ===========================================================================

def validate_email(email: str) -> bool:
    """Valide le format d'une adresse email."""
    return bool(EMAIL_REGEX.match(email.strip()))


def validate_form_data(form_data: dict) -> tuple[bool, str]:
    """
    Valide les données du formulaire d'authentification.

    Returns:
        Tuple (is_valid, error_message)
    """
    # Champs obligatoires
    required_fields = ['prenom', 'nom', 'email']
    for field in required_fields:
        if not form_data.get(field, '').strip():
            return False, f"Le champ '{field}' est obligatoire."

    # Validation email
    if not validate_email(form_data.get('email', '')):
        return False, "L'adresse email n'est pas valide."

    # Consentement CGU obligatoire
    if not form_data.get('accept_cgu'):
        return False, "Vous devez accepter les Conditions Générales d'Utilisation."

    return True, ""


def create_user_session(ip_client: str, user_data: dict) -> str:
    """
    Crée une session utilisateur avec les données collectées.

    Args:
        ip_client: Adresse IP du client
        user_data: Données du formulaire (prenom, nom, email, etc.)

    Returns:
        ID de session généré
    """
    # Données utilisateur pour la session
    session_data = {
        'user_id': str(uuid.uuid4()),
        'user_name': f"{user_data['prenom']} {user_data['nom']}",
        'user_email': user_data['email'],
        'accept_cgu': user_data.get('accept_cgu', False),
        'accept_data_usage': user_data.get('accept_data_usage', False),
        'ip_client': ip_client,
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(minutes=SESSION_DURATION_MINUTES)).isoformat()
    }

    # Créer la session via session_manager
    session_id = session_manager.create_session(ip_client, session_data, SESSION_DURATION_MINUTES)

    app.logger.info(f"Session créée pour {ip_client}: {session_data['user_name']} ({session_data['user_email']})")

    return session_id


# ===========================================================================
# ROUTES FLASK
# ===========================================================================

@app.route("/portail", methods=["GET"])
def portail():
    """
    Page principale du portail d'authentification.

    Affiche le formulaire de connexion avec :
    - Champs prénom, nom, email
    - Case à cocher CGU obligatoire
    - Case optionnelle pour usage des données
    - Lien vers les CGU complètes
    """
    redirect_url = request.args.get('redirect_url', '')
    return render_template('login.html', redirect_url=redirect_url)


@app.route("/portail/auth", methods=["POST"])
def auth():
    """
    Traitement du formulaire d'authentification.

    Valide les données, crée une session, et redirige vers l'URL originale.
    """
    try:
        # Récupération des données du formulaire
        form_data = {
            'prenom': request.form.get('prenom', '').strip(),
            'nom': request.form.get('nom', '').strip(),
            'email': request.form.get('email', '').strip(),
            'accept_cgu': request.form.get('accept_cgu') == 'on',
            'accept_data_usage': request.form.get('accept_data_usage') == 'on'
        }

        # Validation des données
        is_valid, error_msg = validate_form_data(form_data)
        if not is_valid:
            flash(error_msg, 'error')
            return redirect(url_for('portail', redirect_url=request.form.get('redirect_url', '')))

        # Récupération de l'IP client
        ip_client = request.remote_addr

        # Création de la session
        session_id = create_user_session(ip_client, form_data)

        # Message de succès
        flash('Authentification réussie! Vous allez être redirigé.', 'success')

        # Redirection vers l'URL originale ou page d'accueil
        redirect_url = request.form.get('redirect_url', '')
        if redirect_url and redirect_url.startswith(('http://', 'https://')):
            return redirect(redirect_url)
        else:
            return redirect(url_for('dashboard'))

    except Exception as e:
        app.logger.error(f"Erreur lors de l'authentification: {e}")
        flash('Une erreur est survenue. Veuillez réessayer.', 'error')
        return redirect(url_for('portail'))


@app.route("/portail/status", methods=["GET"])
def status():
    """
    Retourne le statut de session de l'IP appelante en JSON.

    Format de réponse:
    {
        "authenticated": true/false,
        "user_name": "Prénom Nom",
        "expires_at": "2026-04-17T15:30:00",
        "time_remaining_minutes": 25,
        "ip_client": "192.168.1.100"
    }
    """
    ip_client = request.remote_addr
    session_info = session_manager.get_session_info(ip_client)

    if session_info:
        try:
            expires_at = datetime.fromisoformat(session_info.get('expires_at', ''))
            time_remaining = max(0, int((expires_at - datetime.now()).total_seconds() / 60))

            response = {
                "authenticated": True,
                "user_name": session_info.get('user_name', 'Utilisateur'),
                "expires_at": session_info.get('expires_at'),
                "time_remaining_minutes": time_remaining,
                "ip_client": ip_client
            }
        except (ValueError, TypeError):
            response = {"authenticated": False, "error": "Session invalide"}
    else:
        response = {"authenticated": False}

    return jsonify(response)


@app.route("/portail/logout", methods=["GET"])
def logout():
    """
    Invalide la session de l'IP appelante et affiche une page de confirmation.
    """
    ip_client = request.remote_addr

    # Invalidation de la session
    success = session_manager.logout(ip_client)

    if success:
        app.logger.info(f"Session invalidée pour {ip_client}")
        flash('Vous avez été déconnecté avec succès.', 'info')
    else:
        flash('Aucune session active trouvée.', 'warning')

    return render_template('logout.html')


@app.route("/portail/cgu", methods=["GET"])
def cgu():
    """
    Affiche la page complète des Conditions Générales d'Utilisation.
    """
    return render_template('cgu.html')


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """
    Page d'accueil après authentification (placeholder).
    """
    ip_client = request.remote_addr
    session_info = session_manager.get_session_info(ip_client)

    if not session_info:
        return redirect(url_for('portail'))

    return render_template('dashboard.html', session=session_info)


# ===========================================================================
# GESTION D'ERREURS
# ===========================================================================

@app.errorhandler(404)
def page_not_found(e):
    """Gestionnaire d'erreur 404."""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    """Gestionnaire d'erreur 500."""
    app.logger.error(f"Erreur 500: {e}")
    return render_template('500.html'), 500


# ===========================================================================
# POINT D'ENTRÉE
# ===========================================================================

if __name__ == "__main__":
    app.logger.info("=" * 60)
    app.logger.info("DÉMARRAGE DU PORTAIL FLASK NETCAP")
    app.logger.info("=" * 60)
    app.logger.info(f"Port: 5000")
    app.logger.info(f"Session duration: {SESSION_DURATION_MINUTES} minutes")
    app.logger.info("=" * 60)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True  # À désactiver en production
    )