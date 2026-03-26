"""
Local LLM client — connects to Ollama running locally or in Docker.

To use LLaMA locally:
    docker run -d -p 11434:11434 ollama/ollama
    docker exec ollama ollama pull llama3.2

Then set in .env:
    LOCAL_LLM_ENABLED=true
    LOCAL_LLM_MODEL=llama3.2
    LOCAL_LLM_BASE_URL=http://localhost:11434/v1
"""

from langchain_openai import ChatOpenAI
from app.models.base import BaseLLMClient
from app.config.settings import get_settings

settings = get_settings()


class LocalLLMClient(BaseLLMClient):
    """
    Uses OpenAI-compatible API that Ollama exposes.
    No special SDK needed — same interface as OpenAI.
    """

    def __init__(self, model: str | None = None):
        self.model = model or settings.local_llm_model
        self._llm = ChatOpenAI(
            model=self.model,
            base_url=settings.local_llm_base_url,
            api_key="ollama",           # Ollama doesn't need a real key
            temperature=0,
        )

    async def complete(self, messages: list[dict], temperature: float = 0.0) -> str:
        try:
            response = await self._llm.ainvoke(messages)
            return response.content
        except Exception as e:
            raise RuntimeError(f"Local LLM ({self.model}) failed: {str(e)}")

    async def complete_structured(self, messages: list[dict], schema: type, temperature: float = 0.0):
        try:
            llm = self._llm.with_structured_output(schema)
            return await llm.ainvoke(messages)
        except Exception as e:
            raise RuntimeError(f"Local LLM structured output failed: {str(e)}")
