"""
Service de génération d'embeddings
"""
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from ..config import get_settings


class EmbeddingService:
    """
    Service pour générer des embeddings de texte
    Utilise uniquement des modèles locaux gratuits (sentence-transformers)
    """

    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.embedding_provider
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        """Charge le modèle local à la demande"""
        if self.provider != "local":
            raise ValueError("Seul le provider d'embeddings local est supporté")

        if self._model is None:
            self._model = SentenceTransformer(self.settings.embedding_model)
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """
        Génère un embedding pour un texte unique
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Génère des embeddings pour une liste de textes
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calcule la similarité cosinus entre deux embeddings
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))

    def get_embedding_dimension(self) -> int:
        """Retourne la dimension des embeddings"""
        return self.model.get_sentence_embedding_dimension()
