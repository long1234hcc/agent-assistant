import os
from datetime import datetime
from dotenv import load_dotenv

from agents.core.agent import Agent
from agents.core.history import History
from agents.core.session import Session
from agents.models.base import GenAIModel
from agents.mcp.registry import Registry
from agents.prompts.builder import PromptBuilder
from agents.tools.todoist.tool import (
    get_all_tasks,
    get_overdue_tasks,
    get_tasks_by_date,
)

load_dotenv()


def create_todoist_agent() -> Agent:
    """
    Factory function — khởi tạo và trả về TodoistAgent đã setup sẵn.
    Agent này chỉ biết làm việc với Todoist domain.
    Được dùng bởi OrchestratorAgent như một tool.
    """

    # Registry riêng — chỉ chứa tools Todoist
    registry = Registry()
    registry.register("get_all_tasks", get_all_tasks)
    registry.register("get_overdue_tasks", get_overdue_tasks)
    registry.register("get_tasks_by_date", get_tasks_by_date)

    return Agent(
        # Session riêng để không conflict với Orchestrator
        session=Session(session_id="todoist_agent"),

        # History ngắn — sub-agent không cần nhớ nhiều
        history=History(max_length=20),

        prompt_builder=PromptBuilder(),

        llm=GenAIModel(
            model_name="gemini-3-flash-preview",
            api_key=os.environ.get("GEMINI_API_KEY"),
        ),

        tools_registry=registry,

        prompt_params={
            "agent_name": "Todoist Agent",
            "persona": (
                "You are a focused task manager assistant. "
                "Your only job is to fetch and summarize tasks from Todoist. "
                "Use the available tools to get task data, then IMMEDIATELY summarize the results as text. "
                "Do NOT call the same tool more than once. "
                "After getting data from any tool, write your summary and stop."
            ),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "language": "Vietnamese",
        },

        # Sub-agent không cần reflect —
        # Orchestrator là người đánh giá kết quả cuối cùng
        enable_reflection=False,
    )
