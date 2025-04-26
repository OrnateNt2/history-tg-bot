import aiosqlite
from typing import Optional, List, Tuple
from config import DATABASE_PATH

# ────────────────────────── схема ──────────────────────────
# progress:
#   user_id   INTEGER
#   story_id  TEXT
#   node_id   TEXT
#   inventory TEXT   (через «,»)
#   is_finished INTEGER 0/1
#   PK (user_id, story_id)


async def init_db() -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS progress (
                user_id     INTEGER,
                story_id    TEXT,
                node_id     TEXT,
                inventory   TEXT,
                is_finished INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, story_id)
            )
            """
        )
        await db.commit()


# ────────────────────────── CRUD ──────────────────────────
async def get_progress(
    user_id: int, story_id: str
) -> Optional[Tuple[str, str, str, int]]:
    """Возвращает (story_id, node_id, inventory, is_finished) либо None"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT story_id, node_id, inventory, is_finished "
            "FROM progress WHERE user_id=? AND story_id=?",
            (user_id, story_id),
        )
        return await cur.fetchone()


async def set_progress(
    user_id: int,
    story_id: str,
    node_id: str,
    inventory: List[str],
    finished: bool = False,
) -> None:
    inv = ",".join(inventory)
    fin = 1 if finished else 0
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO progress (user_id, story_id, node_id, inventory, is_finished)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, story_id) DO UPDATE SET
                node_id     = excluded.node_id,
                inventory   = excluded.inventory,
                is_finished = excluded.is_finished
            """,
            (user_id, story_id, node_id, inv, fin),
        )
        await db.commit()


async def list_user_stories(
    user_id: int,
) -> List[Tuple[str, int]]:
    """Список (story_id, is_finished) для пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT story_id, is_finished FROM progress WHERE user_id=?",
            (user_id,),
        )
        return await cur.fetchall()
