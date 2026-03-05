
import os
import json
import datetime
import requests
from google import genai
from google.genai import typesD
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIG
# ============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN")
MODEL          = "gemini-3-flash-preview"
SESSION_FILE   = "default_session.jsonl"

# ============================================================
# TOOLS
# ============================================================

def search_github_repositories(query: str = "AI agent", days: int = 30, limit: int = 10) -> list[dict]:
    """
    Tìm GitHub repos trending theo query và khoảng thời gian.
    Trả về list các repo info.
    """
    from datetime import datetime, timedelta

    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    url     = "https://api.github.com/search/repositories"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    params  = {
        "q": f"{query} created:>{since_date} stars:>10",
        "sort": "stars",
        "order": "desc",
        "per_page": limit
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    results = []
    for item in response.json().get("items", []):
        results.append({
            "name":        item.get("full_name"),
            "stars":       item.get("stargazers_count"),
            "forks":       item.get("forks_count"),
            "description": item.get("description"),
            "language":    item.get("language"),
            "url":         item.get("html_url"),
            "topics":      item.get("topics", []),
        })

    return results


def get_readme(repo_full_name: str) -> str:
    """
    Lấy nội dung README của repo từ GitHub API.
    repo_full_name: "owner/repo" — ví dụ "openai/openai-python"
    Trả về nội dung README dạng plain text.
    """
    url     = f"https://api.github.com/repos/{repo_full_name}/readme"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.raw+json"  # trả về raw text thay vì base64
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 404:
        return "README not found."

    response.raise_for_status()
    return response.text[:3000]  # giới hạn 3000 ký tự để không overflow context


# ============================================================
# TOOL REGISTRY
# Map tên tool (string) → function thật
# LLM sẽ trả về tên tool, agent dùng registry để gọi đúng function
# ============================================================

TOOL_REGISTRY = {
    "search_github_repositories": search_github_repositories,
    "get_readme": get_readme,
}

# ============================================================
# PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a Research Agent that helps users find and summarize trending GitHub repositories.

## Available Tools
- search_github_repositories(query, days, limit): Search trending GitHub repos
- get_readme(repo_full_name): Get README content of a specific repo

## Scaling Rules — classify EVERY user request into one of these:

EASY: User asks a simple question answerable without tools (definitions, explanations, general knowledge)
→ Respond directly with text. Do NOT call any tool.

MEDIUM: User wants to find or summarize repos — requires 1-2 tool calls
→ Call the appropriate tool(s), then summarize the results.

HARD: User wants deep research, comparison, or multi-step analysis
→ First output a numbered PLAN, then execute each step using tools.

## Output Format

For EASY:
Answer directly.

For MEDIUM:
TOOL_CALL: <tool_name>
TOOL_INPUT: <json input>

For HARD:
PLAN:
1. <step 1>
2. <step 2>
...
Then execute step by step using TOOL_CALL format above.

## When you have enough information, summarize clearly and concisely.
"""

# ============================================================
# LLM
# ============================================================

def call_llm(messages: list[dict]) -> str:
    """
    Gọi Gemini với conversation history.
    messages: [{"role": "user"/"model", "content": "..."}]
    Trả về response text.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Convert sang format của Gemini
    contents = []
    for msg in messages:
        contents.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        thinking_config=types.ThinkingConfig(thinking_level="LOW"),  # LOW cho skeleton, tiết kiệm token
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=config,
    )

    return response.text

# ============================================================
# PARSER
# Parse output của LLM → tách tool call ra nếu có
# ============================================================

def parse_llm_output(text: str) -> dict:
    """
    Parse LLM output.
    Trả về:
    {
        "type": "text" | "tool_call" | "plan",
        "content": "...",         # nếu type == text
        "tool_name": "...",       # nếu type == tool_call
        "tool_input": {...},      # nếu type == tool_call
        "plan": "...",            # nếu type == plan
    }
    """
    text = text.strip()

    # Check tool call
    if "TOOL_CALL:" in text:
        lines = text.split("\n")
        tool_name  = None
        tool_input = {}

        for i, line in enumerate(lines):
            if line.startswith("TOOL_CALL:"):
                tool_name = line.replace("TOOL_CALL:", "").strip()
            if line.startswith("TOOL_INPUT:"):
                raw = line.replace("TOOL_INPUT:", "").strip()
                try:
                    tool_input = json.loads(raw)
                except json.JSONDecodeError:
                    tool_input = {"raw": raw}

        return {"type": "tool_call", "tool_name": tool_name, "tool_input": tool_input}

    # Check plan
    if text.startswith("PLAN:"):
        return {"type": "plan", "plan": text}

    # Default: plain text answer
    return {"type": "text", "content": text}


# ============================================================
# SESSION — lưu history dạng JSONL
# ============================================================

def save_to_session(entry: dict):
    """
    Append 1 entry vào JSONL file.
    Mỗi dòng là 1 JSON object độc lập.
    """
    session_dir = os.path.dirname(SESSION_FILE)
    if session_dir:
        os.makedirs(session_dir, exist_ok=True)

    entry["timestamp"] = datetime.datetime.now().isoformat()

    with open(SESSION_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_session() -> list[dict]:
    """
    Load toàn bộ session history từ JSONL file.
    Trả về list các entry.
    """
    if not os.path.exists(SESSION_FILE):
        return []

    entries = []
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    return entries


# ============================================================
# AGENT LOOP
# ============================================================

def run_agent(user_input: str):
    """
    Main agent loop.
    1. Nhận user input
    2. Gọi LLM
    3. Parse output → tool call hay text?
    4. Nếu tool call → gọi tool → đưa result lại cho LLM
    5. Lặp lại cho đến khi có final answer
    6. Lưu vào session
    """
    print(f"\n{'='*50}")
    print(f"User: {user_input}")
    print(f"{'='*50}\n")

    messages      = [{"role": "user", "content": user_input}]
    tools_used    = []
    max_iterations = 5  # tránh infinite loop
    iteration      = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"[Iteration {iteration}] Calling LLM...")

        llm_output = call_llm(messages)
        print(f"[LLM Output]\n{llm_output}\n")

        parsed = parse_llm_output(llm_output)

        # Case 1: LLM trả về plan (HARD task)
        if parsed["type"] == "plan":
            print("[Agent] Task is HARD — plan rendered.")
            print(llm_output)

            # Lưu session
            save_to_session({
                "user_input": user_input,
                "type": "plan",
                "plan": parsed["plan"],
                "tools_used": tools_used,
            })
            return

        # Case 2: LLM muốn gọi tool
        if parsed["type"] == "tool_call":
            tool_name  = parsed["tool_name"]
            tool_input = parsed["tool_input"]

            print(f"[Agent] Calling tool: {tool_name} with input: {tool_input}")

            if tool_name not in TOOL_REGISTRY:
                observation = f"Error: tool '{tool_name}' not found in registry."
            else:
                try:
                    result      = TOOL_REGISTRY[tool_name](**tool_input)
                    observation = json.dumps(result, ensure_ascii=False)
                except Exception as e:
                    observation = f"Error calling tool: {str(e)}"

            tools_used.append({"tool": tool_name, "input": tool_input})
            print(f"[Tool Result] {observation[:300]}...\n")  # preview 300 ký tự

            # Đưa kết quả tool vào conversation để LLM đọc tiếp
            messages.append({"role": "model",   "content": llm_output})
            messages.append({"role": "user",    "content": f"Tool result:\n{observation}"})
            continue

        # Case 3: LLM trả về final answer
        if parsed["type"] == "text":
            print(f"[Final Answer]\n{parsed['content']}")

            # Lưu session
            save_to_session({
                "user_input":   user_input,
                "type":         "answer",
                "answer":       parsed["content"],
                "tools_used":   tools_used,
            })
            return

    print("[Agent] Max iterations reached — stopping.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    user_input = input("Nhập câu hỏi của bạn: ")
    run_agent(user_input)