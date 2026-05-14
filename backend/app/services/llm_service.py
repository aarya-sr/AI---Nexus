import logging
import time

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from app.config import MODEL_ROUTING, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds
RETRYABLE_ERRORS = (APIError, APITimeoutError, RateLimitError)


class LLMService:
    """OpenRouter client with model-per-agent routing and retry."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._client = OpenAI(
            api_key=api_key or OPENROUTER_API_KEY,
            base_url=base_url or OPENROUTER_BASE_URL,
        )

    def get_model(self, agent_name: str) -> str:
        model = MODEL_ROUTING.get(agent_name)
        if not model:
            raise ValueError(
                f"Unknown agent '{agent_name}'. Valid: {list(MODEL_ROUTING.keys())}"
            )
        return model

    def call(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """Single LLM call routed to the correct model for this agent."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.call_with_messages(
            agent_name, messages, temperature, max_tokens, json_mode
        )

    def call_with_messages(
        self,
        agent_name: str,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """LLM call with full message history. Retries with exponential backoff."""
        model = self.get_model(agent_name)

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except RETRYABLE_ERRORS as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2**attempt)
                    logger.warning(
                        "LLM call failed (agent=%s, model=%s, attempt=%d/%d): %s. Retrying in %.1fs",
                        agent_name, model, attempt + 1, MAX_RETRIES + 1, e, delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "LLM call failed after %d attempts (agent=%s, model=%s): %s",
                        MAX_RETRIES + 1, agent_name, model, e,
                    )
        raise last_error  # type: ignore[misc]
