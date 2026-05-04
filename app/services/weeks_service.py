from datetime import date, timedelta

from app.db import (
    count_assignments_for_scheduled_raid,
    count_scheduled_raids_for_week,
    create_raid_assignment,
    create_scheduled_raid,
    create_week,
    delete_scheduled_raid,
    delete_week,
    get_connection,
)

WEEK_NOT_FOUND_MESSAGE = "No week found."
WEEK_CREATE_SUCCESS_MESSAGE = "Week creation successful"
WEEK_CREATE_FAILURE_MESSAGE = "Week creation failed"
SCHEDULED_RAID_CREATE_SUCCESS_MESSAGE = "Scheduled raid creation successful"
SCHEDULED_RAID_CREATE_FAILURE_MESSAGE = "Scheduled raid creation failed"
ASSIGNMENT_SUCCESS_MESSAGE = "Assignment successful"
ASSIGNMENT_FAILURE_MESSAGE = "Assignment failed"


def get_default_week_start_date() -> str:
    # Business rule: planning defaults to next Wednesday (never the current day).
    today = date.today()
    days_until_wednesday = (2 - today.weekday()) % 7

    if days_until_wednesday == 0:
        days_until_wednesday = 7

    next_wednesday = today + timedelta(days=days_until_wednesday)
    return next_wednesday.isoformat()


def get_weeks_page_data() -> dict:
    with get_connection() as connection:
        week_rows = connection.execute(
            "SELECT * FROM weeks ORDER BY start_date DESC"
        ).fetchall()

    return {
        "weeks": [dict(row) for row in week_rows],
        "default_start_date": get_default_week_start_date(),
    }


def create_week_record(start_date: str, notes: str):
    create_week(start_date, notes)


def _group_scheduled_raids_by_day(scheduled_raids: list[dict]) -> list[dict]:
    # Converts a flat raid list into day buckets so the UI can render sectioned blocks.
    day_groups = []
    current_day = None
    current_raids = []

    for raid in scheduled_raids:
        raid_day = raid.get("day")
        if raid_day != current_day:
            if current_day is not None:
                day_groups.append({"day": current_day, "raids": current_raids})
            current_day = raid_day
            current_raids = [raid]
        else:
            current_raids.append(raid)

    if current_day is not None:
        day_groups.append({"day": current_day, "raids": current_raids})

    return day_groups


def _fetch_week_row(connection, week_id: int):
    week_row = connection.execute(
        "SELECT * FROM weeks WHERE id = ?",
        (week_id,),
    ).fetchone()
    if not week_row:
        raise ValueError(WEEK_NOT_FOUND_MESSAGE)
    return week_row


def _fetch_raid_definition_rows(connection):
    return connection.execute(
        "SELECT * FROM raid_definitions ORDER BY min_item_level DESC"
    ).fetchall()


def _fetch_scheduled_rows(connection, week_id: int):
    return connection.execute(
        """SELECT
            scheduled_raids.id,
            scheduled_raids.week_id,
            scheduled_raids.raid_definition_id,
            scheduled_raids.day,
            scheduled_raids.group_number,
            scheduled_raids.start_time,
            scheduled_raids.notes,
            scheduled_raids.sort_order,
            raid_definitions.title AS raid_title,
            raid_definitions.difficulty AS raid_difficulty,
            raid_definitions.player_count AS player_count
        FROM scheduled_raids
        JOIN raid_definitions
            ON scheduled_raids.raid_definition_id = raid_definitions.id
        WHERE scheduled_raids.week_id = ?
        ORDER BY CASE scheduled_raids.day
            WHEN "Wed" THEN 1
            WHEN "Thu" THEN 2
            WHEN "Fri" THEN 3
            WHEN "Sat" THEN 4
            WHEN "Sun" THEN 5
            ELSE 99
        END ASC,
        scheduled_raids.sort_order ASC""",
        (week_id,),
    ).fetchall()


def _fetch_character_rows(connection):
    return connection.execute(
        """SELECT
            characters.*,
            members.display_name AS member_name
            FROM characters
            JOIN members ON characters.member_id = members.id
            WHERE characters.is_active = 1
            ORDER BY characters.item_level DESC, characters.name ASC
        """
    ).fetchall()


def _fetch_assignment_rows(connection, week_id: int):
    return connection.execute(
        """
        SELECT
            scheduled_raid_assignments.id,
            scheduled_raid_assignments.scheduled_raid_id,
            scheduled_raid_assignments.character_id,
            scheduled_raid_assignments.slot_order,
            scheduled_raid_assignments.notes,
            characters.name AS character_name,
            characters.class_name,
            characters.item_level,
            characters.combat_role,
            characters.combat_power_score
        FROM scheduled_raid_assignments
        JOIN characters
            ON scheduled_raid_assignments.character_id = characters.id
        WHERE scheduled_raid_assignments.scheduled_raid_id IN (
            SELECT id
            FROM scheduled_raids
            WHERE week_id = ?
        )
        ORDER BY scheduled_raid_assignments.scheduled_raid_id ASC,
                    scheduled_raid_assignments.slot_order ASC
        """,
        (week_id,),
    ).fetchall()


def get_week_detail_page_data(week_id: int) -> dict:
    # Single read model for week detail: pulls week, raids, active characters, and assignments.
    with get_connection() as connection:
        week_row = _fetch_week_row(connection, week_id)
        raid_def_rows = _fetch_raid_definition_rows(connection)
        scheduled_rows = _fetch_scheduled_rows(connection, week_id)
        character_rows = _fetch_character_rows(connection)
        assignments_rows = _fetch_assignment_rows(connection, week_id)

    week = dict(week_row)
    raid_definitions = [dict(row) for row in raid_def_rows]
    scheduled_raids = [dict(row) for row in scheduled_rows]
    characters = [dict(row) for row in character_rows]
    scheduled_raid_assignments = [dict(row) for row in assignments_rows]

    return {
        "week": week,
        "raid_definitions": raid_definitions,
        "scheduled_raids": scheduled_raids,
        "day_groups": _group_scheduled_raids_by_day(scheduled_raids),
        "characters": characters,
        "scheduled_raid_assignments": scheduled_raid_assignments,
    }


def create_scheduled_raid_record(
    week_id: int,
    raid_definition_id: int,
    day: str,
    group_number: int,
    start_time: str | None,
    notes: str,
    sort_order: int,
):
    create_scheduled_raid(
        week_id,
        raid_definition_id,
        day,
        group_number,
        start_time,
        notes,
        sort_order,
    )


def create_assignment_record(
    scheduled_raid_id: int,
    character_id: int,
    slot_order: int,
    notes: str,
):
    create_raid_assignment(scheduled_raid_id, character_id, slot_order, notes)


def get_scheduled_raid_assignment_count(scheduled_raid_id: int) -> int:
    return count_assignments_for_scheduled_raid(scheduled_raid_id)


def get_week_scheduled_raid_count(week_id: int) -> int:
    return count_scheduled_raids_for_week(week_id)


def delete_week_record(week_id: int):
    # Guard against deleting a week that still has dependent scheduled raids.
    if count_scheduled_raids_for_week(week_id) > 0:
        raise ValueError("This week has scheduled raids and cannot be deleted.")

    delete_week(week_id)


def force_delete_week_record(week_id: int):
    delete_week(week_id)


def delete_scheduled_raid_record(scheduled_raid_id: int):
    if count_assignments_for_scheduled_raid(scheduled_raid_id) > 0:
        raise ValueError("This scheduled raid has assignments and cannot be deleted.")

    delete_scheduled_raid(scheduled_raid_id)


def force_delete_scheduled_raid_record(scheduled_raid_id: int):
    delete_scheduled_raid(scheduled_raid_id)
