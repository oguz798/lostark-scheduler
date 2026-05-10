from app.domain.days import PLANNER_DAYS
from app.db import (
    get_connection,
    upsert_week_member_availability,
)

VALID_AVAILABILITY_STATUSES = {"available", "unavailable", "after"}


def fetch_week_member_availability(week_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                members.id AS member_id,
                members.display_name AS member_name,
                week_member_availability.day,
                week_member_availability.status,
                week_member_availability.available_after,
                week_member_availability.notes
            FROM members
            LEFT JOIN week_member_availability
                ON week_member_availability.member_id = members.id
                AND week_member_availability.week_id = ?
            ORDER BY members.display_name ASC
            """,
            (week_id,),
        ).fetchall()

    availability_by_member = {}

    for row in rows:
        member_id = row["member_id"]

        if member_id not in availability_by_member:
            availability_by_member[member_id] = {
                "member_id": member_id,
                "member_name": row["member_name"],
                "days": {
                    day: {
                        "status": "available",
                        "available_after": "",
                        "notes": "",
                    }
                    for day in PLANNER_DAYS
                },
            }

        if row["day"] in PLANNER_DAYS:
            availability_by_member[member_id]["days"][row["day"]] = {
                "status": row["status"] or "available",
                "available_after": row["available_after"] or "",
                "notes": row["notes"] or "",
            }

    return list(availability_by_member.values())


def validate_availability_input(
    day: str,
    status: str,
    available_after: str | None,
) -> tuple[str, str, str | None]:
    clean_day = (day or "").strip()
    clean_status = (status or "available").strip().lower()
    clean_available_after = (available_after or "").strip() or None

    if clean_day not in PLANNER_DAYS:
        raise ValueError("Day must be Wed, Thu, Fri, Sat, or Sun.")

    if clean_status not in VALID_AVAILABILITY_STATUSES:
        raise ValueError("Status must be available, unavailable, or after.")

    if clean_status == "after" and not clean_available_after:
        raise ValueError("Available-after time is required when status is after.")

    if clean_status != "after":
        clean_available_after = None

    if clean_available_after is not None:
        _validate_hhmm(clean_available_after)

    return clean_day, clean_status, clean_available_after


def _validate_hhmm(value: str) -> None:
    parts = value.split(":")

    if len(parts) != 2:
        raise ValueError("Available-after time must use HH:MM format.")

    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        raise ValueError("Available-after time must use HH:MM format.")

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("Available-after time must be a valid 24-hour time.")


def update_week_member_availability(
    week_id: int,
    member_id: int,
    day: str,
    status: str,
    available_after: str | None,
    notes: str | None,
) -> None:
    clean_day, clean_status, clean_available_after = validate_availability_input(
        day,
        status,
        available_after,
    )
    upsert_week_member_availability(
        week_id=week_id,
        member_id=member_id,
        day=clean_day,
        status=clean_status,
        available_after=clean_available_after,
        notes=(notes or "").strip(),
    )
