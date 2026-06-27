import json
import os
import uuid
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)
SESSIONS_DIR = os.path.join(
    BASE_DIR,
    ".agent",
    "sessions"
)

AGENTS_PATH = os.path.join(
    BASE_DIR,
    "AGENTS.md"
)


def create_session() -> str:
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    return uuid.uuid4().hex[:8]


def save_session(session_id: str, messages: list, title: str = "Untitled") -> None:
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    data ={
            "id":session_id,
            "title":title,
            "updated_at":datetime.now(timezone.utc).isoformat(),
            "messages":messages,
        }
    path = os.path.join(
        SESSIONS_DIR, f"{session_id}.json"
    )
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        



def load_session(session_id: str) -> dict:
    path=os.path.join(
        SESSIONS_DIR, f"{session_id}.json"
    )
    if not os.path.exists(path):
        raise FileNotFoundError(f"Session '{session_id}' not found.")
    with open(path, 'r', encoding='utf-8') as f:
        my_data=json.load(f)
        return my_data


def list_sessions() -> list[dict]:
    my_list=[]
    temp = os.listdir(SESSIONS_DIR)
    for my_file in temp:
        if not my_file.endswith(".json"):
            continue
        session_id=my_file[:-5]
        to_save=load_session(session_id)
        my_list.append(to_save)
    my_list.sort(
        key=lambda x: x["updated_at"],
        reverse=True
    )
    return my_list

