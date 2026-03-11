import os
from datetime import date
from dotenv import load_dotenv
from todoist_api_python.api import TodoistAPI

load_dotenv()

INBOX_ID = "6g86j8F6cGWp3RF5"


def _get_api() -> TodoistAPI:
    return TodoistAPI(os.environ.get("TODOIST_API_KEY"))


def get_all_tasks() -> str:
    """Get all current tasks from Todoist Inbox.

    Use this tool when the user wants to see all their pending tasks,
    get an overview of their workload, or summarize what they need to do.

    Returns:
        Formatted string listing all tasks with their due dates.
    """
    api = _get_api()
    tasks = [t for page in api.get_tasks() for t in page]
    inbox = [t for t in tasks if t.project_id == INBOX_ID]

    if not inbox:
        return "Không có task nào trong Inbox."

    lines = []
    for t in inbox:
        due = t.due.string if t.due else "Không có deadline"
        lines.append(f"- {t.content} | Due: {due}")

    return "\n".join(lines)


def get_overdue_tasks() -> str:
    """Get all overdue tasks from Todoist.

    Use this tool when the user wants to know which tasks are past their
    deadline and need immediate attention.

    Returns:
        Formatted string listing overdue tasks with their due dates.
    """
    api = _get_api()
    tasks = [t for page in api.get_tasks() for t in page]

    overdue = [
        t for t in tasks
        if t.due and t.due.date < date.today()
    ]

    if not overdue:
        return "Không có task nào quá hạn."

    lines = [f"- {t.content} | Due: {t.due.string}" for t in overdue]
    return "\n".join(lines)


def get_tasks_by_date(date_str: str) -> str:
    """Get tasks due on a specific date from Todoist.

    Use this tool when the user asks about tasks for a specific day,
    e.g. 'what do I have tomorrow' or 'tasks for 2026-03-15'.

    Args:
        date_str: Date in format YYYY-MM-DD. Example: "2026-03-15"

    Returns:
        Formatted string listing tasks due on that date.
    """
    api = _get_api()
    tasks = [t for page in api.get_tasks() for t in page]

    matched = [
        t for t in tasks
        if t.due and str(t.due.date) == date_str
    ]

    if not matched:
        return f"Không có task nào vào ngày {date_str}."

    lines = [f"- {t.content}" for t in matched]
    return "\n".join(lines)
