import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.integrations.llm.client import LLMClient, LLMUnavailable
from app.integrations.pdf.parser import ParsedPage, ParsedPDF
from app.schemas.intelligence import Classification
from app.services.document_classifier import classify_document, content_cue


def test_classification_uses_source_and_structured_response():
    parsed = ParsedPDF([ParsedPage(1, "Commercial Invoice\nInvoice reference\nINV-1", False)])
    assert content_cue(parsed) == "COMMERCIAL_INVOICE"

    def respond(request):
        body = json.loads(request.content)
        assert body["response_format"]["type"] == "json_schema"
        assert "INV-1" in body["messages"][1]["content"]
        assert "expected_decision" not in body["messages"][1]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "document_type": "COMMERCIAL_INVOICE",
                                    "confidence": 0.98,
                                    "reason": "Invoice heading",
                                }
                            )
                        },
                    }
                ]
            },
        )

    settings = Settings(
        _env_file=None,
        llm_api_url="https://example.invalid/v1",
        llm_model="test",
        llm_api_key=SecretStr("test-only"),
    )
    client = LLMClient(settings, httpx.MockTransport(respond))
    result = classify_document(client, parsed)
    assert result.document_type == "COMMERCIAL_INVOICE"
    client.close()


@pytest.mark.parametrize(
    "payload",
    [
        {"document_type": "SANCTIONS", "confidence": 0.9, "reason": "x"},
        {"document_type": "OTHER", "confidence": "0.9", "reason": "x"},
        {"document_type": "OTHER", "confidence": 1.2, "reason": "x"},
        {"document_type": "OTHER", "confidence": 0.9, "reason": "x", "decision": "PASS"},
    ],
)
def test_invalid_classification_is_rejected(payload):
    with pytest.raises(ValueError):
        Classification.model_validate(payload, strict=True)


def test_unvalidated_llm_output_is_not_accepted():
    client = LLMClient(
        Settings(
            _env_file=None,
            llm_api_url="https://example.invalid/v1",
            llm_model="test",
            llm_api_key=SecretStr("test-only"),
        ),
        httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"choices": [{"message": {"content": "```json {} ```"}}]}
            )
        ),
    )
    with pytest.raises(LLMUnavailable):
        classify_document(client, ParsedPDF([ParsedPage(1, "unknown", False)]))
    client.close()


def test_truncated_json_is_retried_once_with_a_bounded_budget():
    calls = []

    def respond(request):
        calls.append(json.loads(request.content)["max_tokens"])
        content = (
            "{"
            if len(calls) == 1
            else json.dumps(
                {"document_type": "OTHER", "confidence": 0.5, "reason": "Unknown heading"}
            )
        )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "length" if len(calls) == 1 else "stop",
                        "message": {"content": content},
                    }
                ]
            },
        )

    client = LLMClient(
        Settings(
            _env_file=None,
            llm_api_url="https://example.invalid/v1",
            llm_model="test",
            llm_api_key=SecretStr("test-only"),
        ),
        httpx.MockTransport(respond),
    )
    result = client.structured([], Classification, max_tokens=1000)
    assert result.document_type == "OTHER"
    assert calls == [1000, 2000]
    client.close()
