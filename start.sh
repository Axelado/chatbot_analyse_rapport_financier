#!/bin/bash
# Script de démarrage du chatbot

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📊 Chatbot Analyse Financière${NC}"
echo ""

# Vérifie si l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Création de l'environnement virtuel...${NC}"
    python3 -m venv venv
fi

# Active l'environnement
source venv/bin/activate

# Installe les dépendances si nécessaire
if [ ! -f "venv/.installed" ]; then
    echo -e "${GREEN}Installation des dépendances...${NC}"
    pip install -r requirements.txt
    touch venv/.installed
fi

# Vérifie le fichier .env
if [ ! -f ".env" ]; then
    echo -e "${GREEN}Création du fichier .env depuis .env.example${NC}"
    cp .env.example .env
fi

# Lit le modèle Ollama configuré dans .env
OLLAMA_MODEL=$(grep -E '^OLLAMA_MODEL=' .env | tail -1 | cut -d '=' -f 2- | tr -d '\r')
if [ -z "$OLLAMA_MODEL" ]; then
    OLLAMA_MODEL="llama3.2:3b"
fi

# Vérifie Ollama (LLM local gratuit)
if ! command -v ollama >/dev/null 2>&1; then
    echo "⚠️  Ollama n'est pas installé."
    echo "   Installez-le depuis https://ollama.com puis lancez: ollama pull $OLLAMA_MODEL"
else
    if ! ollama list >/dev/null 2>&1; then
        echo "⚠️  Ollama est installé mais le service ne répond pas."
        echo "   Lancez Ollama (ou 'ollama serve') avant d'utiliser le chat."
    else
        INSTALLED_MODELS=$(ollama list | awk 'NR>1 {print $1}')
        if ! echo "$INSTALLED_MODELS" | grep -qx "$OLLAMA_MODEL"; then
            echo "⚠️  Le modèle configuré '$OLLAMA_MODEL' n'est pas installé."
            if [ -n "$INSTALLED_MODELS" ]; then
                FIRST_INSTALLED_MODEL=$(echo "$INSTALLED_MODELS" | head -n1)
                echo "   Modèle local disponible: $FIRST_INSTALLED_MODEL"
                echo "   Le backend utilisera automatiquement un fallback vers un modèle disponible."
            else
                echo "   Aucun modèle local détecté."
            fi
            echo "   Pour installer le modèle configuré: ollama pull $OLLAMA_MODEL"
        fi
    fi
fi

# Crée les répertoires nécessaires
mkdir -p data/reports data/chroma_db

echo ""
echo -e "${GREEN}Démarrage du serveur...${NC}"
echo "Interface Web: http://localhost:8000"
echo "Documentation API: http://localhost:8000/docs"
echo ""

# Lance le serveur
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
