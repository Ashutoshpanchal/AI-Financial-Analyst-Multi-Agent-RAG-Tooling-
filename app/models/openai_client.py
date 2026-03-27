"""
OpenAI LLM client — wraps ChatOpenAI for use via ModelRouter.
Token usage is reported to the active Langfuse generation (if any) so the
Langfuse dashboard can show "Usage by Model" and "Cost by Model" charts.
"""

from langchain_openai import ChatOpenAI
from langfuse.decorators import langfuse_context
from app.models.base import BaseLLMClient
from app.config.settings import get_settings

settings = get_settings()


def _report_usage(response_metadata: dict) -> None:
    """Push token counts into the currently-active Langfuse generation."""
    usage = response_metadata.get("token_usage") or response_metadata.get("usage", {})
    if not usage:
        return
    try:
        langfuse_context.update_current_observation(
            usage={
                "input":  usage.get("prompt_tokens") or usage.get("input_tokens", 0),
                "output": usage.get("completion_tokens") or usage.get("output_tokens", 0),
                "total":  usage.get("total_tokens", 0),
            }
        )
    except Exception:
        pass  # never let observability break the pipeline


class OpenAIClient(BaseLLMClient):

    def __init__(self, model: str):
        self.model = model
        self._llm = ChatOpenAI(
            model=model,
            temperature=0,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

    async def complete(self, messages: list[dict], temperature: float = 0.0) -> str:
        llm = self._llm.with_config({"temperature": temperature})
        response = await llm.ainvoke(messages)
        _report_usage(response.response_metadata)
        return response.content

    async def complete_structured(self, messages: list[dict], schema: type, temperature: float = 0.0):
        # include_raw=True returns {"raw": AIMessage, "parsed": schema_instance}
        llm = self._llm.with_structured_output(schema, include_raw=True)
        result = await llm.ainvoke(messages)
        _report_usage(result["raw"].response_metadata)
        return result["parsed"]

    def with_tools(self, tools: list):
        """Returns LLM instance with tools bound — used by computation agent."""
        return self._llm.bind_tools(tools)
