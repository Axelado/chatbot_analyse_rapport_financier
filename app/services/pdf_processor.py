"""
Service de traitement des documents PDF
"""
import fitz  # PyMuPDF
import re
from typing import List, Optional, Tuple
from pathlib import Path
import hashlib
from datetime import datetime

from ..models.schemas import DocumentMetadata, DocumentChunk
from ..config import get_settings


class PDFProcessor:
    """
    Traite les documents PDF pour extraire le texte et les métadonnées
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.chunk_size = self.settings.chunk_size
        self.chunk_overlap = self.settings.chunk_overlap
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[Tuple[int, str]]:
        """
        Extrait le texte de chaque page du PDF
        
        Returns:
            Liste de tuples (numéro_page, texte)
        """
        pages_content = []
        
        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                # Nettoyage basique du texte
                text = self._clean_text(text)
                if text.strip():
                    pages_content.append((page_num, text))
        
        return pages_content
    
    def _clean_text(self, text: str) -> str:
        """Nettoie le texte extrait"""
        # Supprime les caractères de contrôle
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        # Normalise les espaces
        text = re.sub(r'\s+', ' ', text)
        # Supprime les lignes vides multiples
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    def extract_metadata(
        self, 
        pdf_path: str,
        year: Optional[int] = None,
        country: Optional[str] = None,
        organization: Optional[str] = None
    ) -> DocumentMetadata:
        """
        Extrait les métadonnées du PDF
        """
        path = Path(pdf_path)
        
        with fitz.open(pdf_path) as doc:
            pdf_metadata = doc.metadata
            total_pages = len(doc)
        
        # Extraction du titre depuis les métadonnées ou le nom de fichier
        title = pdf_metadata.get('title', '') or path.stem
        
        # Tentative d'extraction de l'année depuis le titre ou le nom de fichier
        if year is None:
            year_match = re.search(r'20[0-2][0-9]|19[9][0-9]', path.stem + title)
            if year_match:
                year = int(year_match.group())
        
        return DocumentMetadata(
            filename=path.name,
            title=title,
            year=year,
            country=country,
            organization=organization,
            total_pages=total_pages,
            upload_date=datetime.now()
        )
    
    def create_chunks(
        self,
        pages_content: List[Tuple[int, str]],
        metadata: DocumentMetadata
    ) -> List[DocumentChunk]:
        """
        Crée des chunks à partir du contenu des pages
        """
        chunks = []
        chunk_index = 0
        
        for page_num, page_text in pages_content:
            # Divise le texte de la page en chunks
            page_chunks = self._split_text(page_text)
            
            for chunk_text in page_chunks:
                if chunk_text.strip():
                    chunk = DocumentChunk(
                        content=chunk_text,
                        page_number=page_num,
                        chunk_index=chunk_index,
                        metadata=metadata
                    )
                    chunks.append(chunk)
                    chunk_index += 1
        
        return chunks
    
    def _split_text(self, text: str) -> List[str]:
        """
        Divise le texte en chunks avec chevauchement
        """
        chunks = []
        
        # Divise d'abord par paragraphes
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Si le paragraphe seul dépasse la taille max, on le divise
            if len(paragraph) > self.chunk_size:
                # D'abord, ajoute le chunk courant s'il existe
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Divise le long paragraphe
                words = paragraph.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk) + len(word) + 1 <= self.chunk_size:
                        temp_chunk += " " + word if temp_chunk else word
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        # Garde le chevauchement
                        overlap_words = temp_chunk.split()[-self.chunk_overlap//10:] if temp_chunk else []
                        temp_chunk = " ".join(overlap_words + [word])
                
                if temp_chunk:
                    current_chunk = temp_chunk
            else:
                # Ajoute le paragraphe au chunk courant
                if len(current_chunk) + len(paragraph) + 2 <= self.chunk_size:
                    current_chunk += "\n\n" + paragraph if current_chunk else paragraph
                else:
                    # Sauvegarde le chunk courant et commence un nouveau
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    # Chevauchement avec la fin du chunk précédent
                    overlap = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                    current_chunk = overlap + "\n\n" + paragraph if overlap else paragraph
        
        # Ajoute le dernier chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def process_pdf(
        self,
        pdf_path: str,
        year: Optional[int] = None,
        country: Optional[str] = None,
        organization: Optional[str] = None
    ) -> Tuple[DocumentMetadata, List[DocumentChunk]]:
        """
        Traite complètement un PDF: extraction, métadonnées, chunking
        """
        # Extraction des métadonnées
        metadata = self.extract_metadata(pdf_path, year, country, organization)
        
        # Extraction du texte
        pages_content = self.extract_text_from_pdf(pdf_path)
        
        # Création des chunks
        chunks = self.create_chunks(pages_content, metadata)
        
        return metadata, chunks
    
    def generate_document_id(self, pdf_path: str) -> str:
        """Génère un ID unique pour le document"""
        path = Path(pdf_path)
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]
