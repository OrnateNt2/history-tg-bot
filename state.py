from typing import List, Tuple
from database import (
    get_progress, set_progress, list_user_stories,
    get_option_id, inc_stat,
)
from story import Story, get_story, random_success, Option

# ─────────────── старт / резюм ───────────────
async def start_or_resume_story(
    user_id: int, story_id: str
) -> Tuple[Story, str, List[str], bool]:
    saved = await get_progress(user_id, story_id)
    story = get_story(story_id)

    if saved:
        node_id, inv, fin = saved
        inv_list = inv.split(",") if inv else []
        return story, node_id, inv_list, bool(fin)

    first_node = next(iter(story.nodes))
    await set_progress(user_id, story_id, first_node, [], False)
    return story, first_node, [], False


# ─────────────── переход ───────────────
async def advance(
    user_id: int,
    story_id: str,
    current_node_id: str,
    option: Option,
    inventory: List[str],
):
    # проверяем requirement
    if option.required_item and option.required_item not in inventory:
        return None, "У тебя нет нужного предмета!"

    # шанс
    next_id = option.next_id
    if option.chance is not None:
        next_id = option.success_id if random_success(option.chance) else option.fail_id

    if option.add_item and option.add_item not in inventory:
        inventory.append(option.add_item)
    if option.remove_item and option.remove_item in inventory:
        inventory.remove(option.remove_item)

    finished = not bool(get_story(story_id).nodes[next_id].options)
    await set_progress(user_id, story_id, next_id, inventory, finished)

    # +статистика
    oid = await get_option_id(current_node_id, option.text)
    if oid is not None:
        await inc_stat(story_id, current_node_id, oid)

    return next_id, None


async def user_stories(user_id: int):
    return await list_user_stories(user_id)
