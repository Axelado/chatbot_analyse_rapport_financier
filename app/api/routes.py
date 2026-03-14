"""
Routes de l'API FastAPI
"""
import os
import time
import shutil
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse

from ..models.schemas import (
    ChatRequest, ChatResponse, UploadResponse, 
    DocumentInfo, Citation, AnalysisRequest, AnalysisResponse
)
from ..services import (
    PDFProcessor, EmbeddingService, VectorStoreService,
    RetrieverService, LLMService
)
from ..utils.citations import CitationFormatter
from ..config import get_settings

router = APIRouter()

# Services (initialisés une seule fois)
embedding_service = EmbeddingService()
vector_store = VectorStoreService(embedding_service)
retriever = RetrieverService(vector_store, embedding_service)
pdf_processor = PDFProcessor()
llm_service = LLMService()
settings = get_settings()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Point d'entrée principal du chatbot
    """
    start_time = time.time()
    
    try:
        # Récupération du contexte pertinent
        results = retriever.retrieve_with_reranking(
            query=request.question,
            top_k=request.top_k,
            filters=request.filters
        )
        
        if not results:
            return ChatResponse(
                answer="Je n'ai pas trouvé d'informations pertinentes dans les rapports financiers disponibles pour répondre à votre question. Assurez-vous que des documents ont été importés.",
                citations=[],
                confidence_score=0.0,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Construction du contexte
        context = retriever.build_context(results)
        
        # Génération de la réponse
        answer = llm_service.generate_response(
            question=request.question,
            context=context,
            conversation_history=request.conversation_history
        )
        
        # Création des citations
        citations = retriever.create_citations(results)
        
        # Calcul du score de confiance
        avg_relevance = sum(r['similarity_score'] for r in results) / len(results)
        confidence = llm_service.estimate_confidence(
            response=answer,
            num_sources=len(results),
            avg_relevance=avg_relevance
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return ChatResponse(
            answer=answer,
            citations=citations,
            confidence_score=confidence,
            processing_time_ms=processing_time
        )
    
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    year: Optional[int] = Form(None),
    country: Optional[str] = Form(None),
    organization: Optional[str] = Form(None)
):
    """
    Upload et indexation d'un document PDF
    """
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Nom de fichier invalide")

    # Vérifie le type de fichier
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")
    
    # Crée le répertoire de stockage si nécessaire
    reports_dir = Path(settings.reports_directory)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarde le fichier
    file_path = reports_dir / filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Traite le PDF
        metadata, chunks = pdf_processor.process_pdf(
            str(file_path),
            year=year,
            country=country,
            organization=organization
        )
        
        # Indexe les chunks
        chunks_added = vector_store.add_chunks(chunks)
        
        return UploadResponse(
            success=True,
            filename=filename,
            message=f"Document indexé avec succès: {chunks_added} segments créés",
            chunks_created=chunks_added,
            metadata=metadata
        )
    
    except Exception as e:
        # Supprime le fichier en cas d'erreur
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")


@router.get("/documents", response_model=List[dict])
async def list_documents():
    """
    Liste tous les documents indexés
    """
    return vector_store.get_document_list()


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """
    Supprime un document de l'index
    """
    success = vector_store.delete_document(filename)
    
    if success:
        # Supprime aussi le fichier physique
        file_path = Path(settings.reports_directory) / filename
        if file_path.exists():
            file_path.unlink()
        
        return {"success": True, "message": f"Document '{filename}' supprimé"}
    else:
        raise HTTPException(status_code=404, detail="Document non trouvé")


@router.get("/stats")
async def get_stats():
    """
    Retourne les statistiques de la base de connaissances
    """
    return vector_store.get_stats()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    """
    Analyse comparative d'indicateurs économiques
    """
    start_time = time.time()
    
    try:
        # Récupère les données pour chaque indicateur
        results_by_indicator = retriever.retrieve_for_comparison(
            indicators=request.indicators,
            years=request.years,
            countries=request.countries
        )
        
        # Construit le contexte d'analyse
        all_results = []
        context_parts = []
        
        for indicator, results in results_by_indicator.items():
            if results:
                context_parts.append(f"\n=== {indicator.upper()} ===")
                for r in results:
                    all_results.append(r)
                    metadata = r['metadata']
                    context_parts.append(
                        f"[{metadata.get('title', 'Doc')} - {metadata.get('year', '?')}] "
                        f"Page {metadata.get('page_number', '?')}:\n{r['content'][:500]}"
                    )
        
        if not all_results:
            return AnalysisResponse(
                analysis="Aucune donnée disponible pour les indicateurs demandés.",
                data_points=[],
                citations=[]
            )
        
        context = "\n".join(context_parts)
        
        # Génère l'analyse
        analysis = llm_service.generate_analysis(
            data_context=context,
            analysis_type=request.analysis_type
        )
        
        # Crée les citations
        citations = retriever.create_citations(all_results)
        
        # Prépare les points de données
        data_points = [
            {
                "indicator": indicator,
                "sources_count": len(results),
                "years_covered": list(set(
                    r['metadata'].get('year') for r in results if r['metadata'].get('year')
                ))
            }
            for indicator, results in results_by_indicator.items()
        ]
        
        return AnalysisResponse(
            analysis=analysis,
            data_points=data_points,
            citations=citations
        )
    
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search(
    query: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    year: Optional[int] = Query(None),
    country: Optional[str] = Query(None)
):
    """
    Recherche sémantique dans les documents
    """
    filters = {}
    if year:
        filters['year'] = year
    if country:
        filters['country'] = country
    
    results = retriever.retrieve(
        query=query,
        top_k=top_k,
        filters=filters if filters else None
    )
    
    return {
        "query": query,
        "results_count": len(results),
        "results": [
            {
                "content": r['content'][:500] + "..." if len(r['content']) > 500 else r['content'],
                "metadata": r['metadata'],
                "score": r['similarity_score']
            }
            for r in results
        ]
    }


@router.get("/health")
async def health_check():
    """
    Vérification de l'état du service
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider
    }
