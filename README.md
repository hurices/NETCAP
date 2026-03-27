# NetCapt - Portail Captif & Analyse des Comportements Internet

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Sprint](https://img.shields.io/badge/sprint-1-orange.svg)]()

##  Description

NetCapt est un système complet de **portail captif** permettant l'authentification des utilisateurs et l'analyse de leur navigation. Conçu dans le cadre d'un projet de 3ème année, il simule une architecture professionnelle rencontrée en entreprise.

### Fonctionnalités principales

-  **Proxy HTTP intercepteur** : Redirige les utilisateurs non authentifiés vers le portail
-  **Portail d'authentification** : Recueil du consentement RGPD et création de sessions
- **Pipeline d'analyse** : Catégorisation des sites, métriques en temps réel
-  **API REST** : Exposition des données et métriques (FastAPI)
- **Dashboard administrateur** : Supervision temps réel (Tkinter/Matplotlib)

### Conformité RGPD

- Consentement explicite requis avant toute collecte
- Données limitées aux métadonnées (pas de contenu)
- Fenêtre glissante de 4 heures pour les données en mémoire
- Archivage et suppression automatique

## Architecture
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Client │────▶│ Proxy │────▶│ Internet │
│ Navigateur │ │ (8080) │ │ │
└─────────────┘ └──────┬──────┘ └─────────────┘
│ (non auth)
▼
┌─────────────┐
│ Portail │
│ Flask (5000)│
└──────┬──────┘
│ (session créée)
▼
┌─────────────┐ ┌─────────────┐
│ Queue │────▶│ Pipeline │
│ Événements │ │ Pandas │
└─────────────┘ └──────┬──────┘
│
┌─────────────┐ │
│ Dashboard │◀───────────┤
│ Tkinter │ │
└─────────────┘ ▼
┌─────────────┐
│ API │
│ FastAPI │
│ (8000) │
└─────────────┘

## Installation

### Prérequis

- Python 3.10 ou supérieur
- pip (gestionnaire de paquets)

### Étapes

```bash
# Cloner le dépôt
git clone https://github.com/votre-org/netcapt.git
cd netcapt

# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt