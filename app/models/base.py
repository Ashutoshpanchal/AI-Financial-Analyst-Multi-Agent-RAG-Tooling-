"""
Abstract LLM interface — all model clients implement this.
Swapping models never requires changes in agent code.
"""

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.0,
    ) -> str:
        """Send messages and return response text."""
        ...

    @abstractmethod
    async def complete_structured(
        self,
        messages: list[dict],
        schema: type,
        temperature: float = 0.0,
    ):
        """Send messages and return structured output matching schema."""
        ...
