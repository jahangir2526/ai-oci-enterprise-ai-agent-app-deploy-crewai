import json

import pytest
from fastapi.testclient import TestClient

from ai_oci_enterprise_ai_hosted_deployment_crewai import main
from ai_oci_enterprise_ai_hosted_deployment_crewai.crews.content_crew.content_crew import (
    AnswerCrew,
)


client = TestClient(main.app)


def test_health_and_readiness() -> None:
    for path in ("/health", "/ready"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"


def test_chat_returns_json(monkeypatch) -> None:
    monkeypatch.setattr(main, "answer_question", lambda question: f"Answer: {question}")

    response = client.post("/chat", json={"question": "Hello"})

    assert response.status_code == 200
    assert response.json() == {"answer": "Answer: Hello"}
    assert response.headers["content-type"] == "application/json"


def test_chat_returns_sse(monkeypatch) -> None:
    answer = 'বাংলা উত্তর: "Hello"\nSecond line'
    monkeypatch.setattr(main, "answer_question", lambda question: answer)

    response = client.post(
        "/chat",
        json={"question": "Hello"},
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.startswith("data: ")
    assert response.text.endswith("\n\n")
    assert json.loads(response.text.removeprefix("data: ")) == {"answer": answer}


@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "x" * 4_001}])
def test_chat_rejects_invalid_input(monkeypatch, payload) -> None:
    def unexpected_run(question):
        pytest.fail("Invalid input must not run the crew")

    monkeypatch.setattr(main, "answer_question", unexpected_run)
    assert client.post("/chat", json=payload).status_code == 422


def test_chat_runs_draft_then_review(monkeypatch) -> None:
    from crewai import BaseLLM

    calls = []

    class StubLLM(BaseLLM):
        def call(self, messages, **kwargs):
            calls.append(messages)
            answer = "Draft answer" if len(calls) == 1 else "Reviewed answer"
            return f"Final Answer: {answer}"

    monkeypatch.setattr(AnswerCrew, "_llm", lambda self: StubLLM(model="test"))

    response = client.post("/chat", json={"question": "Explain OCI"})

    assert response.status_code == 200
    assert response.json() == {"answer": "Reviewed answer"}
    assert len(calls) == 2
    assert "Explain OCI" in str(calls[0])
    assert "Draft answer" in str(calls[1])


def test_crew_uses_oci_responses_api(monkeypatch) -> None:
    monkeypatch.setenv("OCI_REGION", "ap-osaka-1")
    monkeypatch.setenv("OCI_GENAI_API_KEY", "test-oci-key")
    monkeypatch.setenv("OCI_GENAI_PROJECT_OCID", "ocid1.generativeaiproject.test")
    monkeypatch.setenv("OCI_CHAT_MODEL", "openai.gpt-oss-120b")

    llm = AnswerCrew()._llm()

    assert llm.model == "openai.gpt-oss-120b"
    assert llm.api == "responses"
    assert llm.custom_openai is True
    assert llm.base_url == (
        "https://inference.generativeai.ap-osaka-1.oci.oraclecloud.com/openai/v1"
    )
    assert llm.api_key == "test-oci-key"
    assert llm.project == "ocid1.generativeaiproject.test"
    assert llm.store is False
    assert llm.auto_chain is False
