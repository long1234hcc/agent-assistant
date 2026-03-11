import os
from datetime import datetime
from dotenv import load_dotenv

from agents.core.agent import Agent
from agents.core.history import History
from agents.core.session import Session
from agents.models.base import GenAIModel
from agents.mcp.registry import Registry
from agents.prompts.builder import PromptBuilder
from agents.orchestration.research_agent import create_research_agent
from agents.orchestration.todoist_agent import create_todoist_agent

load_dotenv()


def create_orchestrator() -> Agent:

    # ── Khởi tạo sub-agents ───────────────────────────────────────────────────
    _research = create_research_agent()
    _todoist = create_todoist_agent()

    # ── Wrap bằng named functions ─────────────────────────────────────────────
    # Gemini dùng __name__ + docstring để hiểu tool là gì.
    # Nếu register trực tiếp agent.run thì cả 2 đều tên "run" → lỗi duplicate.
    # Wrap ra function riêng để có tên và docstring rõ ràng.

    def research_agent(input: str) -> str:
        _research.history.clear()
        """Search and summarize GitHub repositories.
        Use this for any question about trending repos, GitHub projects, or open source code."""
        return _research.run(input)

    def todoist_agent(input: str) -> str:
        _todoist.history.clear()
        """Fetch and summarize tasks from Todoist.
        Use this for any question about tasks, todos, deadlines, or work items."""
        return _todoist.run(input)

    # ── Registry của Orchestrator ─────────────────────────────────────────────
    registry = Registry()
    registry.register("research_agent", research_agent)
    registry.register("todoist_agent",  todoist_agent)

    return Agent(
        session=Session(session_id="orchestrator"),
        history=History(max_length=50),
        prompt_builder=PromptBuilder(),

        llm=GenAIModel(
            model_name="gemini-3-flash-preview",
            api_key=os.environ.get("GEMINI_API_KEY"),
        ),

        tools_registry=registry,

        prompt_params={
            "agent_name": "Orchestrator",
            "persona": (
                "You are a coordinator agent. Your job is to understand the user's request "
                "and delegate to the right specialist agent to get the data needed.\n\n"

                "Available agents you can call:\n"
                "- research_agent: handles everything related to GitHub — "
                "trending repos, searching repositories, reading READMEs.\n"
                "- todoist_agent: handles everything related to Todoist tasks — "
                "fetching tasks, overdue items, tasks by specific date.\n\n"

                "Rules:\n"
                "1. Always delegate to the right agent — do NOT answer domain questions yourself.\n"
                "2. Pass a clear, specific instruction to each agent.\n"
                "3. After receiving results from agents, synthesize into a single coherent answer.\n"
                "4. If a question needs multiple agents, call them one by one and combine results."
            ),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "language": "Vietnamese",
        },

        enable_reflection=True,
    )


if __name__ == "__main__":
    orchestrator = create_orchestrator()
    user_input = input("Nhập câu hỏi: ")
    result = orchestrator.run(user_input)
    print(f"\n{result}")
