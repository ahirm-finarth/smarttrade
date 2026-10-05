import json
from typing import TypeVar
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    pass


class LLMClient:
    """Shared OpenAI-compatible client with validated structured document responses."""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        if not settings.llm_configured:
            raise LLMUnavailable("LLM configuration is incomplete")
        url = (settings.llm_api_url or "").rstrip("/")
        parsed = urlsplit(url)
        compatible = settings.llm_protocol == "openai" or (
            settings.llm_protocol == "unconfigured" and parsed.path.endswith("/v1")
        )
        if not compatible:
            raise LLMUnavailable(
                "Endpoint protocol is unknown; set LLM_PROTOCOL after verification"
            )
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.query:
            raise LLMUnavailable("Use an HTTP(S) base URL without embedded credentials or query")
        self.model = settings.llm_model
        self._http = httpx.Client(
            base_url=url + "/",
            timeout=settings.llm_timeout_seconds,
            transport=transport,
            headers={"Authorization": f"Bearer {settings.llm_api_key.get_secret_value()}"},
        )

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self._http.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise LLMUnavailable("LLM request failed; endpoint details are suppressed") from None

    def healthcheck(self) -> dict[str, bool]:
        payload = self._request("GET", "models")
        models = payload.get("data", [])
        return {
            "reachable": True,
            "configured_model_listed": any(
                item.get("id") == self.model for item in models if isinstance(item, dict)
            ),
        }

    def complete(self, messages: list[dict[str, str]], max_tokens: int = 32) -> str:
        payload = self._request(
            "POST",
            "chat/completions",
            json={"model": self.model, "messages": messages, "max_tokens": max_tokens},
        )
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMUnavailable("Unexpected OpenAI-compatible response shape") from None

    def structured(
        self, messages: list[dict[str, str]], schema: type[ResponseModel], max_tokens: int = 4096
    ) -> ResponseModel:
        request = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                },
            },
        }
        payload = self._request("POST", "chat/completions", json=request)
        # Reasoning-capable endpoints can consume the budget before producing JSON.
        # Retry only explicit truncation, once, with a bounded larger budget.
        if payload.get("choices", [{}])[0].get("finish_reason") == "length":
            request["max_tokens"] = min(max_tokens * 2, 16000)
            payload = self._request("POST", "chat/completions", json=request)
        try:
            choice = payload["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ValueError("Truncated output")
            content = choice["message"]["content"]
            # Explicit parsing plus strict validation: no fenced JSON or silent coercion.
            return schema.model_validate(json.loads(content), strict=True)
        except (KeyError, IndexError, TypeError, ValueError, ValidationError):
            raise LLMUnavailable("Model output failed structured schema validation") from None

    def close(self):
        self._http.close()
