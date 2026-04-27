import sqlite3
from datetime import UTC, datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "lostark_scheduler.sqlite3"


def current_timestamp() -> str:
    return datetime.now(UTC).isoformat()


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
                combat_role TEXT,
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS raid_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                player_count INTEGER NOT NULL,
                min_item_level REAL NOT NULL,
                notes TEXT DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS weeks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date TEXT NOT NULL,
                notes TEXT DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_raids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_id INTEGER NOT NULL,
                raid_definition_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                group_number INTEGER NOT NULL,
                start_time TEXT,
                notes TEXT DEFAULT '',
                sort_order INTEGER NOT NULL,
                FOREIGN KEY (week_id) REFERENCES weeks(id),
                FOREIGN KEY (raid_definition_id) REFERENCES raid_definitions(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_raid_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheduled_raid_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                slot_order INTEGER NOT NULL,
                notes TEXT DEFAULT '',
                FOREIGN KEY (scheduled_raid_id) REFERENCES scheduled_raids(id),
                FOREIGN KEY (character_id) REFERENCES characters(id)
            )
            """
        )

def create_raid_assignment(
    scheduled_raid_id: int,
    character_id: int,
    slot_order: int,
    notes: str | None,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO scheduled_raid_assignments (
                scheduled_raid_id,
                character_id,
                slot_order,
                notes
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                scheduled_raid_id,
                character_id,
                slot_order,
                notes,          
            ),
        )
        connection.commit()


def create_scheduled_raid(
    week_id: int,
    raid_definition_id: int,
    day: str,
    group_number: int,
    start_time: str | None,
    notes: str | None,
    sort_order: int,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO scheduled_raids (
                week_id,
                raid_definition_id,
                day,
                group_number,
                start_time,
                notes,
                sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                week_id,
                raid_definition_id,
                day,
                group_number,
                start_time,
                notes,
                sort_order,
            ),
        )
        connection.commit()


def create_raid_definition(
    title: str,
    difficulty: str,
    player_count: int,
    min_item_level: float,
    notes: str | None,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO raid_definitions (
                title,
                difficulty,
                player_count,
                min_item_level,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, difficulty, player_count, min_item_level, notes),
        )
        connection.commit()


def create_week(start_date: str, notes: str):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO weeks (
                start_date,
                notes
            )
            VALUES (?, ?)
            """,
            (start_date, notes),
        )
        connection.commit()


def save_imported_roster(member_id: int, roster_data: dict):
    with get_connection() as connection:
        synced_at = current_timestamp()
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
                    combat_role,
                    combat_power_score,
                    region,
                    world,
                    is_active,
                    source,
                    last_synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    member_id,
                    character.get("name"),
                    character.get("class_name"),
                    character.get("item_level"),
                    character.get("combat_power_id"),
                    character.get("combat_role"),
                    character.get("combat_power_score"),
                    character.get("region")
                    or roster_data.get("matched_character_region"),
                    character.get("server_name")
                    or roster_data.get("matched_character_server_name"),
                    1,
                    "lostark_bible",
                    synced_at,
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
