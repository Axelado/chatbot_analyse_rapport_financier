"""
Schémas Pydantic pour l'API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Rôle du message dans la conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class DocumentMetadata(BaseModel):
    """Métadonnées d'un document PDF"""
    filename: str
    title: Optional[str] = None
    year: Optional[int] = None
    country: Optional[str] = None
    organization: Optional[str] = None
    total_pages: int
    upload_date: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DocumentChunk(BaseModel):
    """Chunk de document avec métadonnées"""
    content: str
    page_number: int
    chunk_index: int
    metadata: DocumentMetadata
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour stockage"""
        return {
            "content": self.content,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "filename": self.metadata.filename,
            "title": self.metadata.title,
            "year": self.metadata.year,
            "country": self.metadata.country,
            "organization": self.metadata.organization,
            "total_pages": self.metadata.total_pages
        }


class Citation(BaseModel):
    """Citation d'une source"""
    document_title: str
    filename: str
    year: Optional[int] = None
    page_number: int
    relevance_score: float
    excerpt: str = Field(description="Extrait du texte source")


class ChatMessage(BaseModel):
    """Message dans la conversation"""
    role: MessageRole
    content: str
    citations: Optional[List[Citation]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """Requête de chat"""
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_history: Optional[List[ChatMessage]] = Field(default_factory=list)
    filters: Optional[dict] = Field(
        default=None,
        description="Filtres optionnels (year, country, etc.)"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Nombre de sources à récupérer")


class ChatResponse(BaseModel):
    """Réponse du chatbot"""
    answer: str
    citations: List[Citation]
    confidence_score: float = Field(ge=0, le=1)
    processing_time_ms: float


class UploadResponse(BaseModel):
    """Réponse après upload d'un document"""
    success: bool
    filename: str
    message: str
    chunks_created: int
    metadata: Optional[DocumentMetadata] = None


class DocumentInfo(BaseModel):
    """Information sur un document indexé"""
    filename: str
    title: Optional[str]
    year: Optional[int]
    country: Optional[str]
    total_pages: int
    chunks_count: int
    upload_date: datetime


class AnalysisRequest(BaseModel):
    """Requête d'analyse comparative"""
    indicators: List[str] = Field(..., min_items=1)
    years: Optional[List[int]] = None
    countries: Optional[List[str]] = None
    analysis_type: str = Field(
        default="comparison",
        description="Type d'analyse: comparison, trend, summary"
    )


class AnalysisResponse(BaseModel):
    """Réponse d'analyse"""
    analysis: str
    data_points: List[dict]
    citations: List[Citation]
    visualization_data: Optional[dict] = None
