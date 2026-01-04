# 1xbet Prediction System

Système de prédiction de matchs de football basé sur l'analyse de données historiques.

## Fonctionnalités

- Récupération automatique des matchs du jour
- Analyse basée sur :
  - Historique des confrontations
  - Classement actuel des équipes
  - Avantage domicile/extérieur
  - Forme récente (5 derniers matchs)
  - Joueurs clés et blessures
  - Performance de l'entraîneur
- Génération de combinés optimisés
- Interface web sécurisée par PIN

## Installation

### Backend (Python)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

1. Copier `.env.example` vers `.env`
2. Ajouter votre clé API football (API-Football ou football-data.org)

### Lancement

```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend
cd frontend
# Ouvrir index.html dans un navigateur ou utiliser un serveur local
python -m http.server 3000
```

## Structure du projet

```
1xbet/
├── backend/
│   ├── main.py              # Point d'entrée FastAPI
│   ├── api/
│   │   └── routes.py        # Routes API
│   ├── services/
│   │   ├── match_fetcher.py # Récupération des matchs
│   │   └── predictor.py     # Moteur de prédiction
│   ├── models/
│   │   └── match.py         # Modèles de données
│   └── data/                # Données en cache
├── frontend/
│   ├── index.html           # Page principale
│   ├── src/
│   │   ├── app.js          # Logique frontend
│   │   └── styles.css      # Styles
│   └── public/             # Assets statiques
└── scripts/                # Scripts utilitaires
```

## API Endpoints

- `GET /api/matches/{date}` - Matchs d'une date donnée
- `GET /api/predictions/{date}` - Prédictions pour une date
- `GET /api/best-combos/{date}` - Meilleurs combinés du jour
- `POST /api/auth` - Vérification du PIN

## License

Projet personnel - Usage privé uniquement
