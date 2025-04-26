import json, random
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict
from config import STORIES_PATH
from database import bulk_upsert_story

@dataclass
class Option:
    text:          str
    next_id:       Optional[str] = None
    add_item:      Optional[str] = None
    remove_item:   Optional[str] = None
    required_item: Optional[str] = None
    chance:        Optional[int] = None          # 0-100
    success_id:    Optional[str] = None
    fail_id:       Optional[str] = None

@dataclass
class Node:
    id:      str
    text:    str
    options: List[Option]

@dataclass
class Story:
    id:    str
    title: str
    nodes: Dict[str, Node]

stories: Dict[str, Story] = {}

def _parse_option(raw) -> Option:
    return Option(
        text          = raw["text"],
        next_id       = raw.get("next_id"),
        add_item      = raw.get("add_item"),
        remove_item   = raw.get("remove_item"),
        required_item = raw.get("required_item"),
        chance        = raw.get("chance"),
        success_id    = raw.get("success_id"),
        fail_id       = raw.get("fail_id"),
    )

def load_stories():
    for p in Path(STORIES_PATH).glob("*.json"):
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        nodes = {
            n["id"]: Node(
                id=n["id"],
                text=n["text"],
                options=[_parse_option(o) for o in n["options"]],
            )
            for n in data["nodes"]
        }
        st = Story(id=data["id"], title=data["title"], nodes=nodes)
        stories[st.id] = st
        bulk_upsert_story(st)              # в БД

def get_story(story_id: str) -> Story:
    return stories[story_id]

def random_success(percentage: int) -> bool:
    return random.randint(1, 100) <= percentage
