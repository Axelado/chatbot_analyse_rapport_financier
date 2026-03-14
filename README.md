# 📊 Chatbot d'analyse de rapports financiers (100% gratuit)

Chatbot RAG pour interroger des rapports financiers PDF, avec citations de sources (document, année, page).

## ✅ Stack utilisée

- Backend API: FastAPI
- LLM local: Ollama (modèle open-source local)
- Embeddings: sentence-transformers (local)
- Base vectorielle: ChromaDB (local)
- Frontend: HTML/CSS/JavaScript

## 🧱 Architecture

```text
chatbot/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/routes.py
│   ├── models/schemas.py
│   ├── services/
│   │   ├── pdf_processor.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   ├── retriever.py
│   │   └── llm_service.py
│   └── utils/citations.py
├── frontend/
├── data/
│   ├── reports/
│   └── chroma_db/
├── requirements.txt
├── .env.example
└── start.sh
```

## 🚀 Installation

### Prérequis

- Python 3.9+
- Ollama installé localement

### 1) Cloner et entrer dans le dossier

```bash
cd chatbot
```

### 2) Créer l'environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3) Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 4) Configurer l'environnement

```bash
cp .env.example .env
```

### 5) Préparer le modèle LLM local

```bash
ollama list
# si aucun modèle compatible n'est présent
ollama pull llama3.2:3b
# ou (qualité supérieure, plus lourd)
ollama pull qwen2.5:7b-instruct-q4_K_M
```

### 6) Lancer le projet

```bash
./start.sh
```

- Interface web: <http://localhost:8000>
- Documentation API: <http://localhost:8000/docs>

## ⚙️ Configuration (.env)

- `LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_MODEL=llama3.2:3b` (ou un modèle présent dans `ollama list`)
- `EMBEDDING_PROVIDER=local`
- `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`
- `CHROMA_PERSIST_DIRECTORY=./data/chroma_db`
- `REPORTS_DIRECTORY=./data/reports`

### Exemple de modèle actuellement utilisé

Si vous avez déjà ce modèle localement, vous pouvez configurer:

```env
OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
```

Le backend tente automatiquement un fallback vers un modèle local disponible si celui de `.env` est absent.

## 📖 Utilisation

### Importer des rapports PDF

1. Ouvrir l'interface web.
1. Cliquer sur "Ajouter un rapport".
1. Importer un fichier PDF.
1. Renseigner si besoin année, pays, organisation.

### Poser des questions

Exemples:

- "Quelle est l'évolution de l'inflation entre 2021 et 2023 ?"
- "Compare la croissance du PIB entre la France et l'Allemagne."
- "Quelles tendances sur la dette publique sont mentionnées ?"

### Analyse comparative

1. Aller dans l'onglet "Analyse".
1. Saisir les indicateurs (ex: `inflation, croissance, dette`).
1. Ajouter des filtres (années/pays) si nécessaire.
1. Lancer l'analyse.

## 🔌 API principale

- `POST /api/upload`: importer un PDF
- `POST /api/chat`: question/réponse avec citations
- `POST /api/analyze`: analyse comparative
- `GET /api/documents`: liste des documents indexés
- `DELETE /api/documents/{filename}`: suppression d'un document
- `GET /api/stats`: statistiques de la base
- `GET /api/health`: statut du service

## ℹ️ Notes importantes

- Tout est local et gratuit (pas d'API payante obligatoire).
- Le premier lancement peut être plus long (chargement du modèle et des embeddings).
- La qualité des réponses dépend fortement de la qualité des PDFs importés.

## 🧯 Dépannage

- Erreur `model '...' not found`:
  - Vérifier la config dans `.env` (`OLLAMA_MODEL=...`).
  - Lister les modèles installés: `ollama list`.
  - Installer le modèle voulu: `ollama pull <nom_du_modele>`.

- `POST /api/chat` ou `POST /api/analyze` retourne `503`:
  - Le LLM local est indisponible ou mal configuré.
  - Vérifier `ollama list` et `OLLAMA_MODEL`.
  - Vérifier que le service Ollama répond.

- Erreur `Impossible de contacter Ollama`:
  - Vérifier que le service Ollama est lancé (`ollama serve` si nécessaire).
  - Vérifier `OLLAMA_BASE_URL` dans `.env`.

- `./start.sh` s'arrête immédiatement (code non nul):
  - Lancer `bash -n start.sh` pour vérifier la syntaxe.
  - Vérifier que l'environnement virtuel est activé: `source venv/bin/activate`.
  - Vérifier qu'aucun autre service n'utilise déjà le port 8000.
  - Relancer ensuite: `./start.sh`.

- Messages `Failed to send telemetry event ...` de ChromaDB:
  - Ce sont des logs non bloquants.
  - L'application continue de fonctionner normalement.
