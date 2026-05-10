from datetime import date, timedelta

from app.db import (
    count_assignments_for_raid_group,
    count_raid_groups_for_week,
    create_raid_assignment,
    create_raid_group,
    update_raid_group_schedule,
    move_raid_assignment,
    swap_raid_assignment,
    create_week,
    delete_raid_group,
    delete_assignment,
    delete_week,
    get_connection,
)

WEEK_NOT_FOUND_MESSAGE = "No week found."
WEEK_CREATE_SUCCESS_MESSAGE = "Week creation successful"
WEEK_CREATE_FAILURE_MESSAGE = "Week creation failed"
RAID_GROUP_CREATE_SUCCESS_MESSAGE = "Raid group creation successful"
RAID_GROUP_CREATE_FAILURE_MESSAGE = "Raid group creation failed"
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


def _fetch_week_row(connection, week_id: int):
    week_row = connection.execute(
        "SELECT * FROM weeks WHERE id = ?",
        (week_id,),
    ).fetchone()
    if not week_row:
        raise ValueError(WEEK_NOT_FOUND_MESSAGE)
    return week_row


def _fetch_raid_rows(connection):
    return connection.execute(
        "SELECT * FROM raids ORDER BY min_item_level DESC"
    ).fetchall()


def _fetch_raid_group_rows(connection, week_id: int):
    return connection.execute(
        """SELECT
            raid_groups.id,
            raid_groups.week_id,
            raid_groups.raid_id,
            raid_groups.day,
            raid_groups.group_number,
            raid_groups.start_time,
            raid_groups.notes,
            raid_groups.sort_order,
            raids.title AS raid_title,
            raids.difficulty AS raid_difficulty,
            raids.player_count AS player_count,
            raids.min_item_level AS min_item_level
        FROM raid_groups
        JOIN raids
            ON raid_groups.raid_id = raids.id
        WHERE raid_groups.week_id = ?
        ORDER BY CASE raid_groups.day
            WHEN "Wed" THEN 1
            WHEN "Thu" THEN 2
            WHEN "Fri" THEN 3
            WHEN "Sat" THEN 4
            WHEN "Sun" THEN 5
            ELSE 99
        END ASC,
        raid_groups.sort_order ASC""",
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
            raid_assignments.id,
            raid_assignments.raid_group_id,
            raid_assignments.character_id,
            raid_assignments.slot_order,
            raid_assignments.notes,
            characters.name AS character_name,
            characters.class_name,
            characters.item_level,
            characters.combat_role,
            characters.combat_power_score,
            members.id AS member_id,
            members.display_name AS member_name
        FROM raid_assignments
        JOIN characters
            ON raid_assignments.character_id = characters.id
        JOIN members
            ON characters.member_id = members.id
        WHERE raid_assignments.raid_group_id IN (
            SELECT id
            FROM raid_groups
            WHERE week_id = ?
        )
        ORDER BY raid_assignments.raid_group_id ASC,
                    raid_assignments.slot_order ASC
        """,
        (week_id,),
    ).fetchall()


def get_week_detail_page_data(week_id: int) -> dict:
    # Single read model for week detail: pulls week, raids, active characters, and assignments.
    with get_connection() as connection:
        week_row = _fetch_week_row(connection, week_id)
        raid_rows = _fetch_raid_rows(connection)
        raid_group_rows = _fetch_raid_group_rows(connection, week_id)
        character_rows = _fetch_character_rows(connection)
        assignments_rows = _fetch_assignment_rows(connection, week_id)

    week = dict(week_row)
    raids = [dict(row) for row in raid_rows]
    raid_groups = [dict(row) for row in raid_group_rows]
    characters = [dict(row) for row in character_rows]
    raid_assignments = [dict(row) for row in assignments_rows]

    return {
        "week": week,
        "raids": raids,
        "raid_groups": raid_groups,
        "characters": characters,
        "raid_assignments": raid_assignments,
    }


def create_raid_group_record(
    week_id: int,
    raid_id: int,
    day: str,
    group_number: int,
    start_time: str | None,
    notes: str,
    sort_order: int,
):
    create_raid_group(
        week_id,
        raid_id,
        day,
        group_number,
        start_time,
        notes,
        sort_order,
    )


def update_raid_group_schedule_record(
    raid_group_id: int,
    day: str,
    start_time: str | None,
    sort_order: int,
):
    normalized_day = (day or "").strip()
    normalized_time = (start_time or "").strip() or None
    normalized_sort_order = int(sort_order or 0)

    if not normalized_day:
        raise ValueError("Day is required.")

    if normalized_sort_order < 0:
        raise ValueError("Sort order cannot be negative.")

    update_raid_group_schedule(
        raid_group_id,
        normalized_day,
        normalized_time,
        normalized_sort_order,
    )


def create_assignment_record(
    raid_group_id: int,
    character_id: int,
    slot_order: int,
    notes: str,
):
    create_raid_assignment(raid_group_id, character_id, slot_order, notes)


def get_raid_group_assignment_count(raid_group_id: int) -> int:
    return count_assignments_for_raid_group(raid_group_id)


def get_week_raid_group_count(week_id: int) -> int:
    return count_raid_groups_for_week(week_id)


def delete_week_record(week_id: int):
    # Guard against deleting a week that still has dependent raid groups.
    if count_raid_groups_for_week(week_id) > 0:
        raise ValueError("This week has raid groups and cannot be deleted.")

    delete_week(week_id)


def force_delete_week_record(week_id: int):
    delete_week(week_id)


def delete_raid_group_record(raid_group_id: int):
    if count_assignments_for_raid_group(raid_group_id) > 0:
        raise ValueError("This group has assignments and cannot be deleted.")

    delete_raid_group(raid_group_id)


def delete_assignment_record(assignment_id):
    delete_assignment(assignment_id)


def move_assignment_to_slot(
    assignment_id: int,
    target_raid_group_id: int,
    target_slot_order: int,
):
    try:
        move_raid_assignment(
            int(assignment_id), int(target_raid_group_id), int(target_slot_order)
        )
    except ValueError as exc:
        raise ValueError(str(exc))
    except Exception as exc:
        raise ValueError(f"Failed to move assignment: {exc}")


def swap_assignments_by_slot(
    source_assignment_id: int,
    target_assignment_id: int,
):

    try:
        swap_raid_assignment(int(source_assignment_id), int(target_assignment_id))
    except ValueError as exc:
        raise ValueError(str(exc))
    except Exception as exc:
        raise ValueError(f"Failed to swap assignments: {exc}")


def force_delete_raid_group_record(raid_group_id: int):
    delete_raid_group(raid_group_id)
