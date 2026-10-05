import httpx
import pytest

from app.core.config import Settings
from app.integrations.llm.client import LLMClient, LLMUnavailable


def configured(**kwargs):
    return Settings(
        _env_file=None,
        llm_api_url="https://example.invalid/v1",
        llm_model="demo-model",
        llm_api_key="test-placeholder",
        **kwargs,
    )


def test_openai_client_paths():
    paths = []

    def handler(request):
        paths.append(request.url.path)
        assert request.headers["Authorization"] == "Bearer test-placeholder"
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "demo-model"}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = LLMClient(configured(), transport=httpx.MockTransport(handler))
    assert client.healthcheck()["configured_model_listed"]
    assert client.complete([{"role": "user", "content": "Reply ok"}]) == "ok"
    assert paths == ["/v1/models", "/v1/chat/completions"]
    client.close()


def test_unknown_protocol_requires_explicit_configuration():
    settings = configured()
    settings.llm_api_url = "https://example.invalid/custom"
    with pytest.raises(LLMUnavailable, match="protocol"):
        LLMClient(settings)


def test_error_suppresses_credentials_and_url():
    client = LLMClient(
        configured(),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(401, json={"error": "private-provider-response"})
        ),
    )
    with pytest.raises(LLMUnavailable) as error:
        client.healthcheck()
    assert "test-placeholder" not in str(error.value)
    assert "example.invalid" not in str(error.value)
    assert "private-provider-response" not in str(error.value)
    client.close()
