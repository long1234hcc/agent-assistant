import json
import os
from datetime import datetime

SESSIONS_PATH = "workspace/sessions_store/sessions.json"


def create(session_key: str) -> dict:

    # Load sessions
    if os.path.exists(SESSIONS_PATH):
        with open(SESSIONS_PATH, "r") as f:
            sessions = json.load(f)
    else:
        sessions = {}

    # Create entry
    entry = {
        "token_count": 0,
        "last_active": datetime.now().isoformat(),
        "status": "active"
    }

    # Insert
    sessions[session_key] = entry

    # Ensure folder exists
    os.makedirs(os.path.dirname(SESSIONS_PATH), exist_ok=True)

    # Save
    with open(SESSIONS_PATH, "w") as f:
        json.dump(sessions, f, indent=2)

    return entry


def get_or_create(session_key: str) -> dict:

    session = get(session_key)

    if session is None:
        session = create(session_key)

    return session


def update(session_key: str, token_count: int) -> None:

    # 1. File không tồn tại → return
    if not os.path.exists(SESSIONS_PATH):
        return

    # Load sessions
    with open(SESSIONS_PATH, "r") as f:
        sessions = json.load(f)

    # Session không tồn tại → return
    if session_key not in sessions:
        return

    # 2. Update fields
    sessions[session_key]["token_count"] = token_count
    sessions[session_key]["last_active"] = datetime.now().isoformat()

    # 3. Save file
    with open(SESSIONS_PATH, "w") as f:
        json.dump(sessions, f, indent=2)
