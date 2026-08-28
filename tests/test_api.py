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


def test_invoke_returns_json(monkeypatch) -> None:
    monkeypatch.setattr(main, "answer_question", lambda question: f"Answer: {question}")

    response = client.post("/invoke", json={"question": "Hello"})

    assert response.status_code == 200
    assert response.json() == {"answer": "Answer: Hello"}
    assert response.headers["content-type"] == "application/json"


def test_invoke_returns_sse(monkeypatch) -> None:
    monkeypatch.setattr(main, "answer_question", lambda question: "Streamed answer")

    response = client.post(
        "/invoke",
        json={"question": "Hello"},
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == 'data: {"answer": "Streamed answer"}\n\n'


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
