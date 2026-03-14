"""
Service LLM pour la génération de réponses
"""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import List, Optional, Dict, Any

from ..config import get_settings
from ..models.schemas import ChatMessage


class LLMService:
    """
    Service de génération de réponses avec LLM local (Ollama)
    """
    
    SYSTEM_PROMPT = """Tu es un assistant spécialisé dans l'analyse de rapports financiers et économiques.
Tu réponds aux questions en te basant UNIQUEMENT sur le contexte fourni (extraits de rapports).

Règles importantes:
1. Base tes réponses exclusivement sur les informations du contexte fourni
2. Cite tes sources en utilisant le format [Source X] correspondant aux extraits
3. Si le contexte ne contient pas assez d'informations, indique-le clairement
4. Sois précis et factuel dans tes réponses
5. Pour les données chiffrées, mentionne toujours l'année et la source
6. Structure tes réponses de manière claire et lisible

Tu peux:
- Comparer des indicateurs entre différentes années ou pays
- Synthétiser des tendances économiques
- Expliquer des concepts économiques mentionnés dans les rapports
- Fournir des analyses basées sur les données disponibles"""

    ANALYSIS_PROMPT = """Tu es un analyste économique expert. Analyse les données suivantes et fournis:
1. Une synthèse comparative claire
2. Les tendances identifiées
3. Des observations clés
4. Les limites de l'analyse basée sur les données disponibles

Utilise les sources fournies et cite-les avec [Source X]."""
    
    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.llm_provider
        self._active_model = self.settings.ollama_model

    def generate_response(
        self,
        question: str,
        context: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        temperature: float = 0.3
    ) -> str:
        """
        Génère une réponse basée sur le contexte fourni
        
        Args:
            question: Question de l'utilisateur
            context: Contexte extrait des documents
            conversation_history: Historique de la conversation
            temperature: Température du modèle (0-1)
        
        Returns:
            Réponse générée
        """
        # Construit les messages
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        
        # Ajoute l'historique de conversation si présent
        if conversation_history:
            for msg in conversation_history[-6:]:  # Garde les 6 derniers messages
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        # Message utilisateur avec contexte
        user_message = f"""Contexte (extraits de rapports financiers):
{context}

Question: {question}

Réponds en te basant sur le contexte ci-dessus. Cite tes sources avec [Source X]."""
        
        messages.append({"role": "user", "content": user_message})

        # Génère la réponse
        if self.provider != "ollama":
            raise ValueError(f"Provider non supporté: {self.provider}. Utilisez 'ollama'.")

        return self._generate_ollama(messages, temperature)

    def _generate_ollama(
        self,
        messages: List[Dict[str, str]],
        temperature: float
    ) -> str:
        """Génère une réponse avec Ollama local"""
        try:
            return self._request_ollama_chat(self._active_model, messages, temperature)
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")

            if exc.code == 404 and "not found" in details.lower():
                installed_models = self._list_installed_models()

                if installed_models:
                    fallback_model = installed_models[0]
                    if fallback_model != self._active_model:
                        print(
                            f"⚠️  Modèle Ollama '{self._active_model}' introuvable. "
                            f"Fallback vers '{fallback_model}'."
                        )
                        self._active_model = fallback_model

                        try:
                            return self._request_ollama_chat(self._active_model, messages, temperature)
                        except HTTPError as retry_exc:
                            retry_details = retry_exc.read().decode("utf-8", errors="ignore")
                            raise RuntimeError(
                                f"Erreur Ollama HTTP {retry_exc.code}: {retry_details}"
                            ) from retry_exc
                        except URLError as retry_exc:
                            raise RuntimeError(
                                "Impossible de contacter Ollama. Vérifiez que le service tourne sur "
                                f"{self.settings.ollama_base_url}"
                            ) from retry_exc

                installed_list = ", ".join(installed_models) if installed_models else "aucun"
                raise RuntimeError(
                    f"Modèle Ollama introuvable: '{self._active_model}'. "
                    f"Modèles installés: {installed_list}. "
                    f"Installez le modèle demandé: ollama pull {self._active_model}"
                ) from exc

            raise RuntimeError(f"Erreur Ollama HTTP {exc.code}: {details}") from exc
        except URLError as exc:
            raise RuntimeError(
                "Impossible de contacter Ollama. Vérifiez que le service tourne sur "
                f"{self.settings.ollama_base_url}"
            ) from exc

    def _request_ollama_chat(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        temperature: float
    ) -> str:
        """Appel HTTP à l'API chat d'Ollama"""
        api_url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        request = Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
            content = data.get("message", {}).get("content", "")
            if not content:
                raise ValueError("Réponse vide reçue depuis Ollama")
            return content

    def _list_installed_models(self) -> List[str]:
        """Retourne la liste des modèles disponibles dans Ollama"""
        api_url = f"{self.settings.ollama_base_url.rstrip('/')}/api/tags"
        request = Request(api_url, method="GET")

        try:
            with urlopen(request, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        models = data.get("models", [])
        model_names: List[str] = []
        for model in models:
            if isinstance(model, dict):
                name = model.get("name")
                if isinstance(name, str) and name:
                    model_names.append(name)
        return model_names

    def generate_analysis(
        self,
        data_context: str,
        analysis_type: str = "comparison",
        specific_instructions: Optional[str] = None
    ) -> str:
        """
        Génère une analyse comparative ou de tendances
        """
        messages = [
            {"role": "system", "content": self.ANALYSIS_PROMPT}
        ]
        
        analysis_instructions = {
            "comparison": "Compare les indicateurs entre les différentes sources/années/pays.",
            "trend": "Identifie et analyse les tendances temporelles dans les données.",
            "summary": "Fournis une synthèse complète des informations disponibles."
        }
        
        instruction = analysis_instructions.get(analysis_type, analysis_instructions["summary"])
        if specific_instructions:
            instruction += f"\n\nInstructions supplémentaires: {specific_instructions}"
        
        user_message = f"""Données à analyser:
{data_context}

Type d'analyse demandé: {analysis_type}
{instruction}"""

        messages.append({"role": "user", "content": user_message})

        return self._generate_ollama(messages, temperature=0.4)

    def extract_indicators(self, question: str) -> List[str]:
        """
        Extrait les indicateurs économiques mentionnés dans une question
        """
        # Liste d'indicateurs économiques courants
        common_indicators = [
            "inflation", "pib", "gdp", "croissance", "chômage", "unemployment",
            "dette", "debt", "déficit", "deficit", "exportations", "importations",
            "balance commerciale", "trade balance", "taux d'intérêt", "interest rate",
            "investissement", "investment", "consommation", "consumption",
            "épargne", "savings", "productivité", "productivity"
        ]
        
        question_lower = question.lower()
        found_indicators = []
        
        for indicator in common_indicators:
            if indicator in question_lower:
                found_indicators.append(indicator)
        
        return found_indicators if found_indicators else [question]
    
    def estimate_confidence(
        self,
        response: str,
        num_sources: int,
        avg_relevance: float
    ) -> float:
        """
        Estime le niveau de confiance de la réponse
        """
        # Facteurs de confiance
        source_factor = min(1.0, num_sources / 3)  # Max avec 3+ sources
        relevance_factor = avg_relevance
        
        # Pénalité si la réponse indique un manque d'information
        uncertainty_phrases = [
            "ne contient pas", "pas d'information", "impossible de",
            "données insuffisantes", "pas mentionné", "aucune donnée"
        ]
        uncertainty_penalty = 0.3 if any(p in response.lower() for p in uncertainty_phrases) else 0
        
        confidence = (0.4 * source_factor + 0.6 * relevance_factor) - uncertainty_penalty
        
        return max(0.1, min(1.0, confidence))
