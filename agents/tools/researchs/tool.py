import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
print(
    f"[DEBUG] GITHUB_TOKEN: {repr(GITHUB_TOKEN[:20] if GITHUB_TOKEN else None)}")


HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}


def search_github_repositories(query: str, days: int = 7, limit: int = 5) -> list[dict]:
    """Search for trending GitHub repositories created recently.

    Use this tool when the user wants to find trending, popular, or recently
    created GitHub repositories on a specific topic or technology.

    Args:
        query: Search keyword or topic. Example: "AI agent", "python", "LLM"
        days: Number of recent days to search within. Default is 7 days.
        limit: Maximum number of repositories to return. Default is 10.

    Returns:
        List of repositories with name, stars, forks, description, language,
        url, and topics.
    """
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    params = {
        "q": f"{query} created:>{since_date} stars:>10",
        "sort": "stars",
        "order": "desc",
        "per_page": limit
    }

    response = requests.get(
        "https://api.github.com/search/repositories",
        headers=HEADERS,
        params=params
    )
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


def get_readme(repo_full_name: str, max_chars: int = 3000) -> str:
    """Get the README content of a specific GitHub repository.

    Use this tool when the user wants to understand what a specific repository
    does, its features, installation steps, or technical details.
    Always use the full repository name in format "owner/repo".

    Args:
        repo_full_name: Full repository name in format "owner/repo".
                        Example: "openai/openai-python", "cloudflare/vinext"
        max_chars: Maximum number of characters to return from README.
                   Default is 3000 to avoid overflowing context window.

    Returns:
        README content as plain text. Returns error message if not found.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/readme"

    # Accept: raw+json → trả về plain text thay vì base64
    headers = {**HEADERS, "Accept": "application/vnd.github.raw+json"}

    response = requests.get(url, headers=headers)

    if response.status_code == 404:
        return f"README not found for repository: {repo_full_name}"

    response.raise_for_status()

    content = response.text
    if len(content) > max_chars:
        content = content[:max_chars] + \
            f"\n\n[... truncated at {max_chars} chars]"

    return content


def research_trending_repositories(topic: str) -> str:
    """Research trending GitHub repositories on a topic and return a structured summary.

    Use this skill when the user wants a complete research report on trending
    repositories for a specific technology or topic. This automatically searches,
    fetches READMEs, and formats results — no additional steps needed.

    Args:
        topic: Technology topic to research. Example: "AI agent", "LLM", "RAG"

    Returns:
        Formatted string with repo list + top 3 README summaries ready to present.
    """
    # Bước 1 — Search cứng, không để LLM tự quyết params
    repos = search_github_repositories(query=topic, days=7, limit=10)

    if not repos:
        return f"No trending repositories found for topic: {topic}"

    # Bước 2 — Lấy README top 3 cứng
    readmes = []
    for repo in repos[:3]:
        readme = get_readme(repo["name"])
        readmes.append({
            "name": repo["name"],
            "readme": readme
        })

    # Bước 3 — Format kết quả thành string cho LLM tóm tắt
    output = f"## Trending repos for: {topic}\n\n"

    output += "### Top Repositories\n"
    for r in repos:
        output += f"- **{r['name']}** ({r['stars']} stars) — {r['description']}\n"

    output += "\n### README Details (Top 3)\n"
    for r in readmes:
        output += f"\n#### {r['name']}\n{r['readme']}\n"

    return output
