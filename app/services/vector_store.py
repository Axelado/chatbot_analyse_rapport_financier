"""
Service de base de données vectorielle avec ChromaDB
"""
from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from pathlib import Path

from ..models.schemas import DocumentChunk, DocumentMetadata
from ..config import get_settings
from .embeddings import EmbeddingService


class VectorStoreService:
    """
    Gère le stockage et la recherche vectorielle avec ChromaDB
    """
    
    COLLECTION_NAME = "financial_reports"
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self.settings = get_settings()
        self.embedding_service = embedding_service or EmbeddingService()
        self._client = None
        self._collection = None
        
        # Crée le répertoire de persistance si nécessaire
        persist_dir = Path(self.settings.chroma_persist_directory)
        persist_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def client(self) -> chromadb.Client:
        """Client ChromaDB persistant"""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.settings.chroma_persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        return self._client
    
    @property
    def collection(self):
        """Collection ChromaDB"""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection
    
    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """
        Ajoute des chunks à la base vectorielle
        
        Returns:
            Nombre de chunks ajoutés
        """
        if not chunks:
            return 0
        
        # Prépare les données
        ids = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            chunk_id = f"{chunk.metadata.filename}_{chunk.chunk_index}"
            ids.append(chunk_id)
            documents.append(chunk.content)
            metadatas.append(chunk.to_dict())
        
        # Génère les embeddings
        embeddings = self.embedding_service.embed_texts(documents)
        
        # Ajoute à la collection
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        
        return len(chunks)
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique dans la base vectorielle
        
        Args:
            query: Requête de recherche
            top_k: Nombre de résultats
            filters: Filtres sur les métadonnées (year, country, etc.)
        
        Returns:
            Liste de résultats avec scores
        """
        # Génère l'embedding de la requête
        query_embedding = self.embedding_service.embed_text(query)
        
        # Construit le filtre ChromaDB
        where_filter = self._build_filter(filters) if filters else None
        
        # Recherche
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Formate les résultats
        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                # Convertit la distance en score de similarité
                distance = results['distances'][0][i]
                similarity = 1 - distance  # ChromaDB retourne la distance cosinus
                
                formatted_results.append({
                    "id": doc_id,
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "similarity_score": max(0, similarity)
                })
        
        return formatted_results
    
    def _build_filter(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Construit le filtre ChromaDB depuis les filtres utilisateur"""
        conditions = []
        
        for key, value in filters.items():
            if value is not None:
                if isinstance(value, list):
                    # Filtre OR pour les listes
                    conditions.append({key: {"$in": value}})
                else:
                    conditions.append({key: {"$eq": value}})
        
        if len(conditions) == 0:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}
    
    def delete_document(self, filename: str) -> bool:
        """
        Supprime tous les chunks d'un document
        """
        try:
            # Récupère tous les IDs associés au document
            results = self.collection.get(
                where={"filename": {"$eq": filename}},
                include=[]
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                return True
            return False
        except Exception:
            return False
    
    def get_document_list(self) -> List[Dict[str, Any]]:
        """
        Retourne la liste des documents indexés
        """
        # Récupère tous les documents
        results = self.collection.get(include=["metadatas"])
        
        if not results['metadatas']:
            return []
        
        # Agrège par document
        documents = {}
        for metadata in results['metadatas']:
            filename = metadata.get('filename')
            if filename not in documents:
                documents[filename] = {
                    "filename": filename,
                    "title": metadata.get('title'),
                    "year": metadata.get('year'),
                    "country": metadata.get('country'),
                    "organization": metadata.get('organization'),
                    "total_pages": metadata.get('total_pages'),
                    "chunks_count": 1
                }
            else:
                documents[filename]["chunks_count"] += 1
        
        return list(documents.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur la base"""
        count = self.collection.count()
        documents = self.get_document_list()
        
        return {
            "total_chunks": count,
            "total_documents": len(documents),
            "documents": documents
        }
    
    def reset(self) -> bool:
        """Réinitialise la collection"""
        try:
            self.client.delete_collection(self.COLLECTION_NAME)
            self._collection = None
            return True
        except Exception:
            return False
