from app.db import (
    count_scheduled_raids_for_definition,
    create_raid_definition,
    delete_raid_definition,
    get_connection,
)


def list_raid_definitions() -> list[dict]:
    with get_connection() as connection:
        raid_rows = connection.execute(
            "SELECT * FROM raid_definitions ORDER BY min_item_level DESC"
        ).fetchall()

    return [dict(row) for row in raid_rows]


def create_raid_definition_record(
    title: str,
    difficulty: str,
    player_count: int,
    min_item_level: float,
    notes: str,
):
    create_raid_definition(title, difficulty, player_count, min_item_level, notes)


def get_raid_definition_usage_count(raid_definition_id: int) -> int:
    return count_scheduled_raids_for_definition(raid_definition_id)


def delete_raid_definition_record(raid_definition_id: int):
    if count_scheduled_raids_for_definition(raid_definition_id) > 0:
        raise ValueError("This raid definition is used by scheduled raids.")

    delete_raid_definition(raid_definition_id)


def force_delete_raid_definition_record(raid_definition_id: int):
    delete_raid_definition(raid_definition_id)
