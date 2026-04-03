# NetCapt

## Description
NetCapt est un système de portail captif permettant
l'authentification des utilisateurs et l'analyse
de leur comportement de navigation.

## Objectifs
- Intercepter le trafic HTTP
- Authentifier les utilisateurs
- Analyser les données de navigation
- Visualiser les résultats en temps réel

## Technologies
- Python
- FastAPI
- Flask
- Pandas
- NumPy
- Tkinter

## Lancement (Sprint 1)

```bash
uvicorn api.main:app --reload
Puis ouvrir :http://127.0.0.1:8000/docs

## Lancement Sprint 2 (Proxy HTTP)

```bash
python proxy/proxy_server.py