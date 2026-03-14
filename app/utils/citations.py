"""
Utilitaires pour la gestion des citations
"""
from typing import List
from ..models.schemas import Citation


class CitationFormatter:
    """
    Formate les citations pour l'affichage
    """
    
    @staticmethod
    def format_citation(citation: Citation, index: int) -> str:
        """
        Formate une citation individuelle
        """
        parts = [f"[{index}]"]
        
        # Titre du document
        parts.append(citation.document_title)
        
        # Année si disponible
        if citation.year:
            parts.append(f"({citation.year})")
        
        # Page
        parts.append(f"- Page {citation.page_number}")
        
        return " ".join(parts)
    
    @staticmethod
    def format_citations_list(citations: List[Citation]) -> str:
        """
        Formate une liste de citations pour l'affichage
        """
        if not citations:
            return "Aucune source citée."
        
        lines = ["**Sources:**"]
        for i, citation in enumerate(citations, 1):
            line = CitationFormatter.format_citation(citation, i)
            lines.append(f"  {line}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_citation_markdown(citation: Citation, index: int) -> str:
        """
        Formate une citation en Markdown
        """
        title = citation.document_title
        year = f" ({citation.year})" if citation.year else ""
        page = f"p. {citation.page_number}"
        score = f"{citation.relevance_score:.0%}"
        
        return f"**[{index}]** *{title}*{year}, {page} — Pertinence: {score}"
    
    @staticmethod
    def format_full_citation(citation: Citation, index: int) -> dict:
        """
        Retourne une citation complète sous forme de dictionnaire
        """
        return {
            "index": index,
            "title": citation.document_title,
            "filename": citation.filename,
            "year": citation.year,
            "page": citation.page_number,
            "relevance": f"{citation.relevance_score:.0%}",
            "excerpt": citation.excerpt,
            "formatted": CitationFormatter.format_citation(citation, index)
        }
    
    @staticmethod
    def extract_citation_references(text: str) -> List[int]:
        """
        Extrait les références de citations [Source X] d'un texte
        """
        import re
        pattern = r'\[Source\s*(\d+)\]'
        matches = re.findall(pattern, text)
        return [int(m) for m in matches]
    
    @staticmethod
    def replace_source_references(
        text: str,
        citations: List[Citation]
    ) -> str:
        """
        Remplace les références [Source X] par des citations formatées
        """
        import re
        
        def replace_match(match):
            source_num = int(match.group(1))
            if 1 <= source_num <= len(citations):
                citation = citations[source_num - 1]
                year_str = f" ({citation.year})" if citation.year else ""
                return f"[{citation.document_title}{year_str}, p.{citation.page_number}]"
            return match.group(0)
        
        pattern = r'\[Source\s*(\d+)\]'
        return re.sub(pattern, replace_match, text)
