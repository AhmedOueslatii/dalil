"""Couche LLM indépendante du fournisseur.

La boucle de l'agent ne manipule que les types neutres définis ici (messages, appels
d'outils, usage). Chaque fournisseur a son adaptateur qui traduit vers son SDK : passer
de Gemini à Claude ou Mistral revient à écrire un nouvel adaptateur, sans toucher à
la boucle ni aux outils.
"""
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from google.genai import types

from app.llm import get_client
from app.retry import call_with_retry
from app.settings import get_settings


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON Schema des arguments


@dataclass
class ToolCall:
    name: str
    args: dict
    # Identifiant fourni par le fournisseur pour apparier appel et résultat ; Gemini
    # ne le renseigne pas toujours, l'appariement se fait alors par nom et par ordre.
    id: str | None = None


@dataclass
class UserMessage:
    text: str


@dataclass
class AssistantTurn:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    latence_ms: int = 0
    # Message natif du fournisseur, rejoué tel quel au tour suivant. Nécessaire pour
    # Gemini : ses « thought signatures » doivent revenir intactes, sinon l'API rejette
    # la suite de la conversation ou le modèle perd le fil de son raisonnement.
    raw: Any = None


@dataclass
class ToolResult:
    name: str
    content: dict
    call_id: str | None = None


@dataclass
class ToolResults:
    results: list[ToolResult]


Message = UserMessage | AssistantTurn | ToolResults


class LLMAdapter(Protocol):
    def complete(self, system: str, messages: list[Message], tools: list[ToolSpec]) -> AssistantTurn: ...


class GeminiAdapter:
    def __init__(self, model: str | None = None):
        self.model = model or get_settings().AGENT_MODEL

    def complete(self, system: str, messages: list[Message], tools: list[ToolSpec]) -> AssistantTurn:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0,
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(name=t.name, description=t.description, parameters_json_schema=t.parameters)
                for t in tools
            ])],
            # C'est notre boucle qui exécute les outils (journalisation, budget,
            # garde-fous), jamais le SDK dans notre dos.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        start = time.monotonic()
        response = call_with_retry(
            get_client().models.generate_content,
            model=self.model,
            contents=to_gemini_contents(messages),
            config=config,
        )
        latence_ms = int((time.monotonic() - start) * 1000)

        content = response.candidates[0].content if response.candidates else None
        parts = (content.parts or []) if content else []
        # response.text n'est pas utilisable ici : il ignore les appels d'outils et
        # émet un avertissement dès qu'il y en a. Les parties « thought » sont le
        # raisonnement interne du modèle, pas la réponse.
        text = "".join(p.text for p in parts if p.text and not p.thought)
        calls = [ToolCall(name=fc.name, args=dict(fc.args or {}), id=fc.id) for fc in (response.function_calls or [])]

        usage = response.usage_metadata
        return AssistantTurn(
            text=text,
            tool_calls=calls,
            tokens_in=(usage.prompt_token_count or 0) if usage else 0,
            # Les tokens de réflexion sont facturés comme des tokens de sortie.
            tokens_out=((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)) if usage else 0,
            latence_ms=latence_ms,
            raw=content,
        )


def to_gemini_contents(messages: list[Message]) -> list[types.Content]:
    contents = []
    for m in messages:
        if isinstance(m, UserMessage):
            contents.append(types.Content(role="user", parts=[types.Part(text=m.text)]))
        elif isinstance(m, AssistantTurn):
            if m.raw is not None:
                contents.append(m.raw)
                continue
            parts = [types.Part(text=m.text)] if m.text else []
            parts += [types.Part(function_call=types.FunctionCall(id=c.id, name=c.name, args=c.args)) for c in m.tool_calls]
            contents.append(types.Content(role="model", parts=parts))
        elif isinstance(m, ToolResults):
            contents.append(types.Content(role="user", parts=[
                types.Part(function_response=types.FunctionResponse(id=r.call_id, name=r.name, response=r.content))
                for r in m.results
            ]))
    return contents
