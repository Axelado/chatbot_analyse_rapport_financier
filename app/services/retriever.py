"""
Service de récupération de contexte (Retriever)
"""
from typing import List, Optional, Dict, Any
from ..models.schemas import Citation
from .vector_store import VectorStoreService
from .embeddings import EmbeddingService


class RetrieverService:
    """
    Service de recherche et récupération de contexte pertinent
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStoreService] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStoreService(self.embedding_service)
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Récupère les passages les plus pertinents pour une requête
        
        Args:
            query: Question de l'utilisateur
            top_k: Nombre maximum de résultats
            filters: Filtres optionnels (year, country, etc.)
            min_score: Score minimum de pertinence
        
        Returns:
            Liste des passages pertinents avec métadonnées et scores
        """
        # Recherche dans la base vectorielle
        results = self.vector_store.search(
            query=query,
            top_k=top_k,
            filters=filters
        )
        
        # Filtre par score minimum
        relevant_results = [
            r for r in results
            if r['similarity_score'] >= min_score
        ]
        
        return relevant_results
    
    def retrieve_with_reranking(
        self,
        query: str,
        top_k: int = 5,
        initial_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère et réordonne les résultats pour améliorer la pertinence
        
        Utilise une stratégie de sur-récupération puis réordonnancement
        """
        # Récupère plus de résultats initialement
        initial_results = self.vector_store.search(
            query=query,
            top_k=initial_k,
            filters=filters
        )
        
        if not initial_results:
            return []
        
        # Réordonnancement simple basé sur la correspondance de mots-clés
        query_words = set(query.lower().split())
        
        for result in initial_results:
            content_words = set(result['content'].lower().split())
            keyword_overlap = len(query_words & content_words) / len(query_words) if query_words else 0
            
            # Score combiné: similarité sémantique + correspondance de mots-clés
            combined_score = 0.7 * result['similarity_score'] + 0.3 * keyword_overlap
            result['combined_score'] = combined_score
        
        # Trie par score combiné
        reranked = sorted(initial_results, key=lambda x: x['combined_score'], reverse=True)
        
        return reranked[:top_k]
    
    def create_citations(self, results: List[Dict[str, Any]]) -> List[Citation]:
        """
        Crée des objets Citation à partir des résultats de recherche
        """
        citations = []
        
        for result in results:
            metadata = result['metadata']
            
            # Extrait un court extrait du contenu
            content = result['content']
            excerpt = content[:300] + "..." if len(content) > 300 else content
            
            citation = Citation(
                document_title=metadata.get('title', metadata.get('filename', 'Unknown')),
                filename=metadata.get('filename', 'Unknown'),
                year=metadata.get('year'),
                page_number=metadata.get('page_number', 0),
                relevance_score=result.get('similarity_score', 0),
                excerpt=excerpt
            )
            citations.append(citation)
        
        return citations
    
    def build_context(
        self,
        results: List[Dict[str, Any]],
        max_context_length: int = 4000
    ) -> str:
        """
        Construit le contexte à passer au LLM à partir des résultats
        """
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            content = result['content']
            
            # Format: [Source X] Document - Page Y
            source_header = f"[Source {i}] {metadata.get('title', metadata.get('filename', 'Document'))} - Page {metadata.get('page_number', '?')}"
            
            if metadata.get('year'):
                source_header += f" ({metadata['year']})"
            
            section = f"{source_header}\n{content}\n"
            
            # Vérifie la limite de longueur
            if current_length + len(section) > max_context_length:
                # Tronque le contenu si nécessaire
                available_space = max_context_length - current_length - len(source_header) - 50
                if available_space > 100:
                    truncated_content = content[:available_space] + "..."
                    section = f"{source_header}\n{truncated_content}\n"
                    context_parts.append(section)
                break
            
            context_parts.append(section)
            current_length += len(section)
        
        return "\n".join(context_parts)
    
    def retrieve_for_comparison(
        self,
        indicators: List[str],
        years: Optional[List[int]] = None,
        countries: Optional[List[str]] = None,
        top_k_per_indicator: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Récupère des données pour une analyse comparative
        """
        results_by_indicator = {}
        
        for indicator in indicators:
            # Construit la requête pour cet indicateur
            query = f"données statistiques {indicator}"
            
            # Construit les filtres
            filters = {}
            if years:
                filters['year'] = years
            if countries:
                filters['country'] = countries
            
            # Récupère les résultats
            results = self.retrieve(
                query=query,
                top_k=top_k_per_indicator * 2,  # Sur-récupère
                filters=filters if filters else None
            )
            
            results_by_indicator[indicator] = results[:top_k_per_indicator]
        
        return results_by_indicator
