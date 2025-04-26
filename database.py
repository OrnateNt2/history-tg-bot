import aiosqlite, sqlite3
from datetime import datetime
from typing import List, Optional, Tuple
from config import DATABASE_PATH


# ─────────────── схема ───────────────
async def init_db() -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY,
                username   TEXT,
                first_name TEXT,
                last_name  TEXT,
                joined_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS stories (
                id    TEXT PRIMARY KEY,
                title TEXT
            );

            CREATE TABLE IF NOT EXISTS nodes (
                id       TEXT PRIMARY KEY,
                story_id TEXT REFERENCES stories(id) ON DELETE CASCADE,
                text     TEXT
            );

            CREATE TABLE IF NOT EXISTS options (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id       TEXT REFERENCES nodes(id) ON DELETE CASCADE,
                text          TEXT,
                next_node_id  TEXT,
                add_item      TEXT,
                remove_item   TEXT,
                required_item TEXT,
                chance        INTEGER,
                success_id    TEXT,
                fail_id       TEXT
            );

            CREATE TABLE IF NOT EXISTS progress (
                user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
                story_id    TEXT    REFERENCES stories(id) ON DELETE CASCADE,
                node_id     TEXT    REFERENCES nodes(id),
                inventory   TEXT,
                is_finished INTEGER DEFAULT 0,
                started_at  TEXT,
                updated_at  TEXT,
                PRIMARY KEY (user_id, story_id)
            );

            CREATE TABLE IF NOT EXISTS stats (
                story_id   TEXT,
                node_id    TEXT,
                option_id  INTEGER,
                selections INTEGER DEFAULT 0,
                PRIMARY KEY (story_id, node_id, option_id),
                FOREIGN KEY (option_id) REFERENCES options(id)
            );
            """
        )
        await db.commit()


# ─────────────── users ───────────────
async def ensure_user(tg_user) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO users(id, username, first_name, last_name, joined_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_name  = excluded.last_name
            """,
            (
                tg_user.id,
                tg_user.username,
                tg_user.first_name,
                tg_user.last_name,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        await db.commit()


# ─────────────── bulk-upsert истории ───────────────
def bulk_upsert_story(story) -> None:
    con = sqlite3.connect(DATABASE_PATH)
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO stories(id,title) VALUES(?,?)", (story.id, story.title))

    for node in story.nodes.values():
        cur.execute("INSERT OR IGNORE INTO nodes(id,story_id,text) VALUES(?,?,?)",
                    (node.id, story.id, node.text))

        for opt in node.options:
            cur.execute(
                """
                SELECT 1 FROM options
                WHERE node_id=? AND text=? AND next_node_id=? AND success_id=? AND fail_id=?
                """,
                (node.id, opt.text, opt.next_id, opt.success_id, opt.fail_id),
            )
            if cur.fetchone() is None:
                cur.execute(
                    """
                    INSERT INTO options(
                      node_id,text,next_node_id,
                      add_item,remove_item,required_item,
                      chance,success_id,fail_id)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        node.id,
                        opt.text,
                        opt.next_id,
                        opt.add_item,
                        opt.remove_item,
                        opt.required_item,
                        opt.chance,
                        opt.success_id,
                        opt.fail_id,
                    ),
                )
    con.commit()
    con.close()


# ─────────────── progress ───────────────
async def get_progress(user_id: int, story_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT node_id, inventory, is_finished FROM progress "
            "WHERE user_id=? AND story_id=?",
            (user_id, story_id),
        )
        return await cur.fetchone()


async def set_progress(
    user_id: int,
    story_id: str,
    node_id: str,
    inventory: List[str],
    finished: bool,
) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    inv = ",".join(inventory)
    fin = 1 if finished else 0
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO progress(user_id,story_id,node_id,inventory,
                                 is_finished,started_at,updated_at)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(user_id,story_id) DO UPDATE SET
              node_id     = excluded.node_id,
              inventory   = excluded.inventory,
              is_finished = excluded.is_finished,
              updated_at  = excluded.updated_at
            """,
            (user_id, story_id, node_id, inv, fin, now, now),
        )
        await db.commit()


async def list_user_stories(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT story_id,is_finished FROM progress WHERE user_id=?",
            (user_id,),
        )
        return await cur.fetchall()


# ─────────────── stats ───────────────
async def get_option_id(node_id: str, text: str) -> Optional[int]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM options WHERE node_id=? AND text=?", (node_id, text)
        )
        row = await cur.fetchone()
        return row[0] if row else None


async def inc_stat(story_id: str, node_id: str, option_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO stats(story_id,node_id,option_id,selections)
            VALUES(?,?,?,1)
            ON CONFLICT(story_id,node_id,option_id)
            DO UPDATE SET selections = selections + 1
            """,
            (story_id, node_id, option_id),
        )
        await db.commit()
