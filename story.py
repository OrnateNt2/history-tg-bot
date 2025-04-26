import json
from pathlib import Path
from config import STORIES_PATH

class Node:
    def __init__(self, _id: str, text: str, options: list[dict]):
        self.id      = _id
        self.text    = text
        self.options = options          # [{'text': str, 'next_id': str}, …]

class Story:
    def __init__(self, _id: str, title: str, nodes: dict[str, Node]):
        self.id    = _id
        self.title = title
        self.nodes = nodes

    def get_node(self, node_id: str) -> Node:
        return self.nodes[node_id]

# id -> Story
stories: dict[str, Story] = {}

def load_stories() -> None:
    """Читает все *.json в STORIES_PATH и кладёт в stories{}."""
    for path in Path(STORIES_PATH).glob("*.json"):
        with open(path, "r", encoding="utf-8") as f:
            data  = json.load(f)
            nodes = {
                n["id"]: Node(n["id"], n["text"], n["options"])
                for n in data["nodes"]
            }
            stories[data["id"]] = Story(data["id"], data["title"], nodes)

def get_story(story_id: str) -> Story:
    return stories[story_id]
