# NetCapt - Portail Captif & Analyse Comportementale Réseau

NetCapt est un système de portail captif modulaire conçu pour la surveillance en temps réel et l'analyse comportementale du trafic réseau. Il combine un proxy HTTP, un pipeline d'analyse de données (Pandas/NumPy) et une interface d'administration moderne (FastAPI + Tkinter).

## 🚀 Architecture du Système

Le projet suit une architecture modulaire inspirée des microservices, assurant une séparation claire des responsabilités :

- **Proxy (`proxy/`)**: Serveur TCP relayant le trafic HTTP, capturant les événements de navigation et redirigeant les utilisateurs non authentifiés vers le portail.
- **Portail (`portail/`)**: Interface Flask permettant l'authentification des utilisateurs et la gestion des sessions initiales.
- **Analyse (`analyse/`)**: Pipeline de traitement de données utilisant Pandas pour l'agrégation en temps réel et NumPy pour la détection d'anomalies via le calcul du Z-score.
- **API (`api/`)**: Interface RESTful (FastAPI) exposant les métriques, la gestion des sessions et la configuration du système.
- **Dashboard (`dashboard/`)**: Application desktop (Tkinter) offrant une visualisation en temps réel du trafic, des alertes de sécurité et des contrôles administratifs.
- **Shared (`shared/`)**: État partagé thread-safe gérant les sessions actives et la file d'attente des événements.

## 🛠 Technologies Utilisées

- **Langage**: Python 3.10+
- **Backend API**: FastAPI, Pydantic, Uvicorn
- **Analyse de Données**: Pandas, NumPy
- **Frontend Portail**: Flask, Jinja2
- **Interface Desktop**: Tkinter, Matplotlib
- **Tests**: Pytest

## 📁 Structure des Dossiers

```text
NETCAP/
├── analyse/          # Pipeline d'analyse et détection d'anomalies
├── api/              # API FastAPI et modèles Pydantic
│   └── routers/      # Endpoints (sessions, analytics, config)
├── dashboard/        # Dashboard Tkinter Matplotlib
├── portail/          # Portail de login Flask
├── proxy/            # Serveur Proxy HTTP
├── shared/           # État partagé et gestion des sessions
├── tests/            # Suite de tests unitaires et d'intégration
├── config.py         # Configuration centralisée
├── requirements.txt  # Dépendances du projet
└── README.md         # Documentation générale
```

## ⚙️ Installation

1. **Cloner le projet** :
   ```bash
   git clone <repository_url>
   cd NETCAP
   ```

2. **Créer un environnement virtuel** :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Sur Linux/Mac
   ```

3. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

## 🚦 Processus de Démarrage Complet

Pour tester l'intégralité des fonctionnalités, suivez scrupuleusement cet ordre de démarrage dans des terminaux séparés :

### 1. API d'Administration & Pipeline (Core)
Ce service est le cœur du système. Il gère la base de données en mémoire, les alertes et le traitement analytique.
```bash
# Activation de l'environnement (si nécessaire)
export PYTHONPATH=.
uvicorn api.main:app --port 8000
```
*Vérifiez que le log affiche : "Pipeline d'analyse démarré"*

### 2. Portail Captif (Authentification)
Fournit l'interface de login pour les nouveaux clients du réseau.
```bash
python -m portail.app
```
*Le portail sera accessible sur http://localhost:5000*

### 3. Proxy HTTP (Interception)
Le moteur qui intercepte le trafic et redirige vers le portail si nécessaire.
```bash
python -m proxy.proxy_server
```
*Le proxy écoute sur le port 8080.*

### 4. Dashboard de Monitoring (Administration)
L'outil visuel pour surveiller tout le système en temps réel.
```bash
python dashboard/dashboard.py
```

---

## 🧪 Scénario de Test Utilisateur

1. **Connexion** : Tentez d'accéder à un site via le proxy (ex: configuré dans votre navigateur sur le port 8080).
2. **Authentification** : Vous devriez être redirigé vers le portail (port 5000). Remplissez le formulaire.
3. **Surveillance** : Ouvrez le Dashboard. Vous verrez votre session apparaître dans l'onglet "Sessions Actives".
4. **Analyse** : Naviguez sur quelques sites. Les graphiques "Top Domaines" et "Trafic" se mettront à jour automatiquement.
5. **Alerte** : Générez un trafic intense. Une alerte apparaîtra dans l'onglet "Alertes" après analyse Z-score.

---

## 👥 Participation au Projet

Répartition approximative de l'effort de développement pour les différentes phases :

| Composant / Sprint | Responsable principal |
|--------------------|-----------------------|
| **Sprints 1, 2, 3** (Proxy, Portail, Base) | 
| **Sprint 4** (API, Pipeline Pandas, NumPy) |
| **Sprint 5** (Dashboard Tkinter, Refactoring) |

**Taux de participation global estimé :**
- **HURICE** : 50% (SPRINT :1,4,5 AVEC TEST FINAL)
- **NATHAN** : 50% (SPRINT:2;3 AVEC LES AMELIORATIONS)
- **CESARD** :--
-**ALIMASS** :--
-  **AMINA** :--

---
**NetCap** — Sécurité et Visibilité Réseau Simplifiées. THANKS!