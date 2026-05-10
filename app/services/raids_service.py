from app.db import (
    count_raid_groups_for_raid,
    create_raid,
    delete_raid,
    get_connection,
)


def list_raids() -> list[dict]:
    with get_connection() as connection:
        raid_rows = connection.execute(
            "SELECT * FROM raids ORDER BY min_item_level DESC"
        ).fetchall()

    return [dict(row) for row in raid_rows]


def create_raid_record(
    title: str,
    difficulty: str,
    player_count: int,
    min_item_level: float,
    notes: str,
):
    create_raid(title, difficulty, player_count, min_item_level, notes)


def get_raid_usage_count(raid_id: int) -> int:
    return count_raid_groups_for_raid(raid_id)


def delete_raid_record(raid_id: int):
    if count_raid_groups_for_raid(raid_id) > 0:
        raise ValueError("This raid is used by raid groups.")

    delete_raid(raid_id)


def force_delete_raid_record(raid_id: int):
    delete_raid(raid_id)
