#!/bin/bash
# Script de lancement du scheduler de prédictions

cd /Users/mac/1xbet/bot

# Activer l'environnement virtuel
source venv/bin/activate

# Lancer le scheduler
echo "🚀 Démarrage du scheduler..."
echo "⏰ Exécution quotidienne à 21:00"
echo "📱 Groupe Telegram: @bel9lil"
echo ""
echo "Pour arrêter: Ctrl+C"
echo "================================"

python scheduler.py
