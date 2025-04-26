from typing import List, Tuple, Optional
from database import get_progress, set_progress, list_user_stories
from story import get_story, Story


async def start_or_resume_story(
    user_id: int, story_id: str
) -> Tuple[Story, str, List[str], bool]:
    """
    Возвращает:
        story, current_node_id, inventory, is_finished
    """
    saved = await get_progress(user_id, story_id)
    story = get_story(story_id)

    if saved:
        _, node_id, inv, fin = saved
        inventory = inv.split(",") if inv else []
        return story, node_id, inventory, bool(fin)

    # ещё не начинал
    first_node = next(iter(story.nodes))
    await set_progress(user_id, story_id, first_node, [], False)
    return story, first_node, [], False


async def advance(
    user_id: int,
    story_id: str,
    next_node: str,
    inventory: List[str],
    finished: bool,
):
    await set_progress(user_id, story_id, next_node, inventory, finished)


async def user_stories(user_id: int):
    """[(story_id, finished_flag)]"""
    return await list_user_stories(user_id)
