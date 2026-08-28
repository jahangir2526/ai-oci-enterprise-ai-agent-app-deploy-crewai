"""Minimal two-agent CrewAI question-answering crew."""

import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv


# Load local development values without overriding an OCI deployment profile.
load_dotenv()


@CrewBase
class AnswerCrew:
    """Draft an answer, then independently review and improve it."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def _llm(self) -> LLM:
        region = os.getenv("OCI_REGION", "us-ashburn-1")
        return LLM(
            model=os.getenv("OCI_CHAT_MODEL", "xai.grok-4.3"),
            custom_openai=True,
            api="responses",
            base_url=(
                f"https://inference.generativeai.{region}.oci.oraclecloud.com/openai/v1"
            ),
            api_key=os.environ["OCI_GENAI_API_KEY"],
            project=os.environ["OCI_GENAI_PROJECT_OCID"],
            store=False,
            auto_chain=False,
        )

    @agent
    def solution_scout(self) -> Agent:
        return Agent(
            config=self.agents_config["solution_scout"],  # type: ignore[index]
            llm=self._llm(),
            tools=[],
            memory=False,
            cache=False,
            max_iter=2,
            verbose=False,
        )

    @agent
    def clarity_editor(self) -> Agent:
        return Agent(
            config=self.agents_config["clarity_editor"],  # type: ignore[index]
            llm=self._llm(),
            tools=[],
            memory=False,
            cache=False,
            max_iter=2,
            verbose=False,
        )

    @task
    def draft_answer(self) -> Task:
        return Task(
            config=self.tasks_config["draft_answer"],  # type: ignore[index]
        )

    @task
    def review_answer(self) -> Task:
        return Task(
            config=self.tasks_config["review_answer"],  # type: ignore[index]
            context=[self.draft_answer()],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            memory=False,
            cache=False,
            verbose=False,
        )
