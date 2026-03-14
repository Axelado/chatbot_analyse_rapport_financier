"""
Point d'entrée principal de l'application FastAPI
Chatbot d'analyse de rapports financiers
"""
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()

# Réduit les logs telemetry ChromaDB non critiques
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

from .api import router
from .config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    settings = get_settings()
    
    # Crée les répertoires nécessaires au démarrage
    Path(settings.reports_directory).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Chatbot Financier démarré")
    print(f"   - LLM: {settings.llm_provider}")
    print(f"   - Embeddings: {settings.embedding_provider}")
    print(f"   - Documents: {settings.reports_directory}")
    
    yield
    
    print("👋 Chatbot Financier arrêté")


# Création de l'application
app = FastAPI(
    title="Chatbot Analyse Financière",
    description="""
    Chatbot intelligent pour l'analyse de rapports financiers et économiques.
    
    ## Fonctionnalités
    
    - **Chat**: Posez des questions sur les rapports financiers
    - **Upload**: Importez des documents PDF pour enrichir la base de connaissances
    - **Analyse**: Comparez des indicateurs économiques entre années/pays
    - **Recherche**: Recherche sémantique dans les documents
    
    ## Sources
    
    Les réponses sont basées sur les rapports financiers importés, avec citation des sources.
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les origines autorisées
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes API
app.include_router(router, prefix="/api", tags=["API"])

# Serveur de fichiers statiques pour le frontend
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    
    @app.get("/")
    async def serve_frontend():
        """Sert l'interface utilisateur"""
        return FileResponse(frontend_path / "index.html")


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
