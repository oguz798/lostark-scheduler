import sqlite3
from datetime import UTC, datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "lostark_scheduler.sqlite3"


# Connection / time helpers
def current_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# Schema init
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
            CREATE TABLE IF NOT EXISTS raids (
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
            CREATE TABLE IF NOT EXISTS raid_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_id INTEGER NOT NULL,
                raid_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                group_number INTEGER NOT NULL,
                start_time TEXT,
                notes TEXT DEFAULT '',
                sort_order INTEGER NOT NULL,
                FOREIGN KEY (week_id) REFERENCES weeks(id),
                FOREIGN KEY (raid_id) REFERENCES raids(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS raid_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raid_group_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                slot_order INTEGER NOT NULL,
                notes TEXT DEFAULT '',
                FOREIGN KEY (raid_group_id) REFERENCES raid_groups(id),
                FOREIGN KEY (character_id) REFERENCES characters(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS week_member_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                available_after TEXT,
                notes TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT,
                UNIQUE (week_id, member_id, day),
                FOREIGN KEY (week_id) REFERENCES weeks(id),
                FOREIGN KEY (member_id) REFERENCES members(id)
            )
            """
        )


# Roster import sync
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


# Create operations
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


def create_raid_assignment(
    raid_group_id: int,
    character_id: int,
    slot_order: int,
    notes: str | None,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO raid_assignments (
                raid_group_id,
                character_id,
                slot_order,
                notes
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                raid_group_id,
                character_id,
                slot_order,
                notes,
            ),
        )
        connection.commit()


def move_raid_assignment(
    assignment_id: int, target_raid_group_id: int, target_slot_order: int
):
    with get_connection() as connection:
        source_row = connection.execute(
            """
            SELECT id
            FROM raid_assignments
            WHERE id = ? 
            """,
            (assignment_id,),
        ).fetchone()

        if source_row is None:
            raise ValueError("Assignment could not be found.")

        target_row = connection.execute(
            """
            SELECT id
            FROM raid_assignments
            WHERE raid_group_id = ? AND slot_order = ?
            """,
            (target_raid_group_id, target_slot_order),
        ).fetchone()

        if target_row is not None:
            raise ValueError("Target slot is occupied.")

        connection.execute(
            """
            UPDATE raid_assignments
            SET raid_group_id = ?, slot_order = ?
            WHERE id = ?
            """,
            (
                target_raid_group_id,
                target_slot_order,
                assignment_id,
            ),
        )

        connection.commit()


def swap_raid_assignment(source_assignment_id: int, target_assignment_id: int):

    with get_connection() as connection:
        source_row = connection.execute(
            """
            SELECT id, raid_group_id, slot_order
            FROM raid_assignments
            WHERE id = ?
            """,
            (source_assignment_id,),
        ).fetchone()
        target_row = connection.execute(
            """
            SELECT id, raid_group_id, slot_order
            FROM raid_assignments
            WHERE id = ?
            """,
            (target_assignment_id,),
        ).fetchone()

        if source_row is None or target_row is None:
            raise ValueError("Swap requires both assignments to exist.")

        source_raid_group_id = int(source_row["raid_group_id"])
        source_slot_order = int(source_row["slot_order"])

        target_raid_group_id = int(target_row["raid_group_id"])
        target_slot_order = int(target_row["slot_order"])

        connection.execute(
            """
            UPDATE raid_assignments
            SET slot_order = -1
            WHERE id = ?
            """,
            (source_assignment_id,),
        )
        connection.execute(
            """
            UPDATE raid_assignments
            SET raid_group_id= ?, slot_order = ?
            WHERE id = ?
            """,
            (source_raid_group_id, source_slot_order, target_assignment_id),
        )
        connection.execute(
            """
            UPDATE raid_assignments
            SET raid_group_id= ?,slot_order = ?
            WHERE id = ?
            """,
            (target_raid_group_id, target_slot_order, source_assignment_id),
        )

        connection.commit()


def create_raid_group(
    week_id: int,
    raid_id: int,
    day: str,
    group_number: int,
    start_time: str | None,
    notes: str | None,
    sort_order: int,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO raid_groups (
                week_id,
                raid_id,
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
                raid_id,
                day,
                group_number,
                start_time,
                notes,
                sort_order,
            ),
        )
        connection.commit()


def update_raid_group_schedule(
    raid_group_id: int,
    day: str,
    start_time: str | None,
    sort_order: int,
):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE raid_groups
            SET day = ?, start_time = ?, sort_order = ?
            WHERE id = ?
            """,
            (
                day,
                start_time,
                sort_order,
                raid_group_id,
            ),
        )
        connection.commit()


def create_raid(
    title: str,
    difficulty: str,
    player_count: int,
    min_item_level: float,
    notes: str | None,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO raids (
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


def upsert_week_member_availability(
    week_id: int,
    member_id: int,
    day: str,
    status: str,
    available_after: str | None,
    notes: str | None,
):
    timestamp = current_timestamp()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO week_member_availability (
                week_id,
                member_id,
                day,
                status,
                available_after,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(week_id, member_id, day)
            DO UPDATE SET
                status = excluded.status,
                available_after = excluded.available_after,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                week_id,
                member_id,
                day,
                status,
                available_after,
                notes,
                timestamp,
                timestamp,
            ),
        )
        connection.commit()


# Count/query helpers
def count_raid_groups_for_raid(raid_id: int) -> int:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM raid_groups WHERE raid_id = ?",
            (raid_id,),
        ).fetchone()

        return row[0]


def count_raid_groups_for_week(week_id: int) -> int:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM raid_groups WHERE week_id = ?",
            (week_id,),
        ).fetchone()

        return row[0]


def count_assignments_for_raid_group(raid_group_id: int) -> int:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM raid_assignments WHERE raid_group_id = ?",
            (raid_group_id,),
        ).fetchone()

        return row[0]


def count_assignments_for_member(member_id: int) -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM raid_assignments
            WHERE character_id IN (
                SELECT id
                FROM characters
                WHERE member_id = ?
            )
            """,
            (member_id,),
        ).fetchone()

        return row[0]


def count_assignments_for_character(character_id: int) -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM raid_assignments
            WHERE character_id = ?
            """,
            (character_id,),
        ).fetchone()

        return row[0]


# Delete operations (cascading behavior)
def delete_raid(raid_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM raid_assignments
            WHERE raid_group_id IN (
                SELECT id
                FROM raid_groups
                WHERE raid_id = ?
            )
            """,
            (raid_id,),
        )
        connection.execute(
            """
            DELETE FROM raid_groups
            WHERE raid_id = ?
            """,
            (raid_id,),
        )
        connection.execute(
            """
            DELETE FROM raids
            WHERE id = ?
            """,
            (raid_id,),
        )
        connection.commit()


def delete_raid_group(raid_group_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM raid_assignments
            WHERE raid_group_id = ?
            """,
            (raid_group_id,),
        )
        connection.execute(
            """
            DELETE FROM raid_groups
            WHERE id = ?
            """,
            (raid_group_id,),
        )
        connection.commit()


def delete_assignment(assignment_id: int):

    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM raid_assignments
            WHERE id = ?
            """,
            (assignment_id,),
        )
        connection.commit()


def delete_week(week_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM week_member_availability
            WHERE week_id = ?
            """,
            (week_id,),
        )
        connection.execute(
            """
            DELETE FROM raid_assignments
            WHERE raid_group_id IN (
                SELECT id
                FROM raid_groups
                WHERE week_id = ?
            )
            """,
            (week_id,),
        )
        connection.execute(
            """
            DELETE FROM raid_groups
            WHERE week_id = ?
            """,
            (week_id,),
        )
        connection.execute(
            """
            DELETE FROM weeks
            WHERE id = ?
            """,
            (week_id,),
        )
        connection.commit()


def delete_member(member_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM week_member_availability
            WHERE member_id = ?
            """,
            (member_id,),
        )
        connection.execute(
            """
            DELETE FROM raid_assignments
            WHERE character_id IN (
                SELECT id
                FROM characters
                WHERE member_id = ?
            )
            """,
            (member_id,),
        )
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


def delete_character(member_id: int, character_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM raid_assignments
            WHERE character_id =?            
            """,
            (character_id,),
        )
        connection.execute(
            """
            DELETE FROM characters
            WHERE id = ? AND member_id = ?
            """,
            (
                character_id,
                member_id,
            ),
        )
        connection.commit()
