import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "lostark_scheduler.sqlite3"


def get_connection():

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                discord_name TEXT,
                region TEXT,
                world TEXT,
                roster_name TEXT,
                notes TEXT DEFAULT '',
                created_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                item_level REAL,
                combat_power_id INTEGER,
                combat_power_score REAL,
                region TEXT,
                world TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                source TEXT,
                last_synced_at TEXT,
                FOREIGN KEY (member_id) REFERENCES members(id)
            )
            """
        )


def save_imported_roster(member_id: int, roster_data: dict):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE members
            SET region = ?, world = ?, roster_name = ?
            WHERE id = ?
            """,
            (
                roster_data.get("matched_character_region"),
                roster_data.get("matched_character_server_name"),
                roster_data.get("matched_character_name"),
                member_id,
            ),
        )
        connection.execute(
            """
            DELETE FROM characters
            WHERE member_id = ?
            """,
            (member_id,),
        )
        for character in roster_data.get("top_characters", []):
            connection.execute(
                """
                INSERT INTO characters (
                    member_id,
                    name,
                    class_name,
                    item_level,
                    combat_power_id,
                    combat_power_score,
                    region,
                    world,
                    is_active,
                    source,
                    last_synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    member_id,
                    character.get("name"),
                    character.get("class_name"),
                    character.get("item_level"),
                    character.get("combat_power_id"),
                    character.get("combat_power_score"),
                    character.get("region") or roster_data.get("matched_character_region"),
                    character.get("server_name")
                    or roster_data.get("matched_character_server_name"),
                    1,
                    "lostark_bible",
                    None,
                ),
            )
        connection.commit()


def delete_member(member_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM characters
            WHERE member_id = ?
            """,
            (member_id,),
        )
        connection.execute(
            """
            DELETE FROM members
            WHERE id = ?
            """,
            (member_id,),
        )
        connection.commit()


def delete_character(character_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM characters
            WHERE id = ?
            """,
            (character_id,),
        )
        connection.commit()
