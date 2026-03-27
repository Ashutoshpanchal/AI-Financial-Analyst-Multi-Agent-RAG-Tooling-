"""
ModelRouter — selects the right LLM for each task type.

Routing rules (config-driven via settings):

  Task type       → Model           → Reason
  ─────────────── → ─────────────── → ──────────────────────────────
  routing         → gpt-4o-mini     → simple classification, cheap
  planning        → gpt-4o          → needs multi-step reasoning
  rag_synthesis   → gpt-4o          → needs to read + synthesize docs
  computation     → gpt-4o          → needs reliable tool-calling
  aggregation     → gpt-4o          → final answer quality matters
  critique        → gpt-4o          → validation needs strong reasoning
  simple          → gpt-4o-mini     → straightforward Q&A, cheap
  local           → llama3.2        → sensitive data / offline mode

Fallback chain:
  local LLM fails → gpt-4o-mini → gpt-4o
"""

from functools import lru_cache
from app.models.base import BaseLLMClient
from app.models.openai_client import OpenAIClient
from app.models.local_client import LocalLLMClient
from app.config.settings import get_settings

settings = get_settings()
model_name ='meta/llama-4-maverick-17b-128e-instruct'

# Task → model name mapping (easy to change without touching agent code)
TASK_MODEL_MAP: dict[str, str] = {
    "routing":       model_name,
    "planning":      model_name,
    "rag_synthesis": model_name,
    "computation":   model_name,
    "aggregation":   model_name,
    "critique":      model_name,
    "simple":        model_name,
    "local":         "local",
}


class ModelRouter:
    """
    Returns the right LLM client for a given task.
    Handles local LLM fallback automatically.
    """

    def get(self, task: str) -> BaseLLMClient:
        """
        Returns a client for the given task type.
        Falls back to OpenAI if local LLM is not enabled.
        """
        model_name = TASK_MODEL_MAP.get(task, "gpt-4o-mini")

        if model_name == "local":
            if settings.local_llm_enabled:
                return LocalLLMClient()
            # Fallback: local not available → use cheap OpenAI model
            model_name = "gpt-4o-mini"

        return OpenAIClient(model=model_name)


    def get_with_fallback(self, task: str, fallback_task: str = "simple") -> BaseLLMClient:
        """
        Try to get the model for `task`, fall back to `fallback_task` on failure.
        Use this in agents that should degrade gracefully.
        """
        try:
            return self.get(task)
        except Exception:
            return self.get(fallback_task)


@lru_cache
def get_model_router() -> ModelRouter:
    return ModelRouter()
