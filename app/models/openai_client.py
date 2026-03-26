"""
OpenAI LLM client — wraps ChatOpenAI for use via ModelRouter.
"""

from langchain_openai import ChatOpenAI
from app.models.base import BaseLLMClient
from app.config.settings import get_settings

settings = get_settings()


class OpenAIClient(BaseLLMClient):

    def __init__(self, model: str):
        self.model = model
        self._llm = ChatOpenAI(
            model=model,
            temperature=0,
            api_key=settings.openai_api_key,
        )

    async def complete(self, messages: list[dict], temperature: float = 0.0) -> str:
        llm = self._llm.with_config({"temperature": temperature})
        response = await llm.ainvoke(messages)
        return response.content

    async def complete_structured(self, messages: list[dict], schema: type, temperature: float = 0.0):
        llm = self._llm.with_structured_output(schema)
        return await llm.ainvoke(messages)

    def with_tools(self, tools: list):
        """Returns LLM instance with tools bound — used by computation agent."""
        return self._llm.bind_tools(tools)
