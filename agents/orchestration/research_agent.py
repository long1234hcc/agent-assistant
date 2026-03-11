import os
from datetime import datetime
from dotenv import load_dotenv

from agents.core.agent import Agent
from agents.core.history import History
from agents.core.session import Session
from agents.models.base import GenAIModel
from agents.mcp.registry import Registry
from agents.prompts.builder import PromptBuilder
from agents.tools.researchs.tool import (
    search_github_repositories,
    get_readme,
    research_trending_repositories,
)

load_dotenv()


def create_research_agent() -> Agent:
    """
    Factory function — khởi tạo và trả về ResearchAgent đã setup sẵn.
    Agent này chỉ biết làm việc với GitHub domain.
    Được dùng bởi OrchestratorAgent như một tool.
    """

    # Registry riêng — chỉ chứa tools GitHub
    registry = Registry()
    registry.register("search_github_repositories", search_github_repositories)
    registry.register("get_readme", get_readme)
    registry.register("research_trending_repositories",
                      research_trending_repositories)

    return Agent(
        # Session riêng để không conflict với Orchestrator
        session=Session(session_id="research_agent"),

        # History ngắn — sub-agent không cần nhớ nhiều
        history=History(max_length=20),

        prompt_builder=PromptBuilder(),

        llm=GenAIModel(
            model_name="gemini-3-flash-preview",
            api_key=os.environ.get("GEMINI_API_KEY"),
        ),

        tools_registry=registry,

        prompt_params={
            "agent_name": "Research Agent",
            "persona": (
                "You are a focused GitHub researcher. "
                "Your only job is to fetch and summarize GitHub data. "
                "Use the available tools to find relevant repositories and return clear, concise results."
            ),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "language": "Vietnamese",
        },

        # Sub-agent không cần reflect —
        # Orchestrator là người đánh giá kết quả cuối cùng
        enable_reflection=False,
    )
