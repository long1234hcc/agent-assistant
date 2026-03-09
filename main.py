import os
from datetime import datetime
from dotenv import load_dotenv

from agents.core.agent import Agent
from agents.core.history import History
from agents.core.session import Session
from agents.models.base import GenAIModel
from agents.mcp.registry import Registry
from agents.prompts.builder import PromptBuilder
from agents.tools.researchs.tool import search_github_repositories, get_readme, research_trending_repositories

load_dotenv()

# ============================================================
# 1. Init components
# ============================================================

session = Session(session_id="default")

history = History(max_length=50)

## Add sesions to history for better context management
all_sessions = session.load()

if all_sessions:
    for entry in all_sessions:
        first   = all_sessions[:1]
        recent  = all_sessions[-3:]
        past    = first + recent
        for entry in past:
            history.add(entry["user_input"], role="user")
            history.add(entry["answer"],role="model")

builder = PromptBuilder()

llm = GenAIModel(
    model_name="gemini-3-flash-preview",
    api_key=os.environ.get("GEMINI_API_KEY")
)

registry = Registry()

# ============================================================
# 2. Register tools
# ============================================================

registry.register("search_github_repositories", search_github_repositories)
registry.register("get_readme", get_readme)
registry.register("research_trending_repositories",
                  research_trending_repositories)


# ============================================================
# 3. Build system prompt params
# ============================================================

prompt_params = {
    "agent_name": "Research Agent",
    "persona":    "You are a concise, insightful researcher. You focus on practical value and avoid unnecessary filler.",
    "date":       datetime.now().strftime("%Y-%m-%d"),
    "language":   "Vietnamese",
}

# ============================================================
# 4. Create agent
# ============================================================

agent = Agent(
    session=session,
    history=history,
    prompt_builder=builder,
    llm=llm,
    tools_registry=registry,
    prompt_params=prompt_params,
)

# ============================================================
# 5. Run
# ============================================================

if __name__ == "__main__":
    user_input = input("Nhập câu hỏi: ")
    result = agent.run(user_input)
    print(f"\n{result}")
