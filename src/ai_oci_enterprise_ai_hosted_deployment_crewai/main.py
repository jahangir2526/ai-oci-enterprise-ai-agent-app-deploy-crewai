"""HTTP entry point for the OCI Generative AI hosted deployment."""

import json
from typing import Annotated

from fastapi import FastAPI, Header, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_oci_enterprise_ai_hosted_deployment_crewai.crews.content_crew.content_crew import (
    AnswerCrew,
)


app = FastAPI(
    title="CrewAI Answer Studio",
    description="A minimal, stateless two-agent question-answering demo.",
    version="1.0.0",
)


class QuestionRequest(BaseModel):
    """Input accepted by the hosted agent."""

    question: str = Field(min_length=1, max_length=4_000)


class AnswerResponse(BaseModel):
    """Response returned by the hosted agent."""

    answer: str


def answer_question(question: str) -> str:
    """Run a new stateless crew and return only its final answer."""
    result = AnswerCrew().crew().kickoff(inputs={"question": question})
    return result.raw


@app.get("/health", include_in_schema=False)
def health() -> Response:
    """OCI liveness probe."""
    return Response(status_code=200, media_type="application/json")


@app.get("/ready", include_in_schema=False)
def ready() -> Response:
    """OCI readiness probe."""
    return Response(status_code=200, media_type="application/json")


@app.post("/invoke", response_model=AnswerResponse)
async def invoke(
    payload: QuestionRequest,
    accept: Annotated[str | None, Header()] = None,
) -> AnswerResponse | StreamingResponse:
    """Answer one question as JSON, or as one SSE event when requested."""
    answer = await run_in_threadpool(answer_question, payload.question)

    if accept and "text/event-stream" in accept.lower():
        event = f"data: {json.dumps({'answer': answer})}\n\n"
        return StreamingResponse(iter([event]), media_type="text/event-stream")

    return AnswerResponse(answer=answer)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Small discovery response for a live demo."""
    return {
        "name": "CrewAI Answer Studio",
        "usage": "POST /invoke with JSON: {\"question\": \"Why is the sky blue?\"}",
    }


def run() -> None:
    """Run the service locally through the ``serve`` project command."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
