"""
Tracked OpenAI wrapper.

Every LLM call goes through here so Langfuse automatically captures:
- model used
- prompt / response
- token usage (prompt + completion tokens)
- estimated cost

Usage:
    result = await tracked_llm_call(
        trace=request.state.trace,
        name="planner_agent",
        model="gpt-4o",
        messages=[{"role": "user", "content": "..."}],
    )
    print(result.content)
"""

import time
from openai import AsyncOpenAI
from langfuse.model import ModelUsage
from app.config.settings import get_settings

settings = get_settings()
openai_client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)


async def tracked_llm_call(
    trace,
    name: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.0,
) -> str:
    """
    Makes an OpenAI chat completion call and logs it as a
    Langfuse Generation under the given trace.

    Returns the response content string.
    """
    # Create generation — marks start of LLM call in the trace
    generation = trace.generation(
        name=name,
        model=model,
        input=messages,
    )

    start_time = time.time()

    try:
        response = await openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )

        latency_ms = round((time.time() - start_time) * 1000, 2)
        content = response.choices[0].message.content

        # End generation — logs output + token usage
        generation.end(
            output=content,
            usage=ModelUsage(
                input=response.usage.prompt_tokens,
                output=response.usage.completion_tokens,
                total=response.usage.total_tokens,
            ),
            metadata={"latency_ms": latency_ms},
        )

        return content

    except Exception as exc:
        generation.end(
            output={"error": str(exc)},
            status_message="error",
        )
        raise exc
