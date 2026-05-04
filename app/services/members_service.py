from datetime import datetime
from dataclasses import asdict


from app.db import (
    get_connection,
    current_timestamp,
    save_imported_roster,
    delete_member,
    delete_character,
)

from app.services.search_service import (
    search_member_rosters,
)

VALID_ROLES = {"", "dps", "sup", "flex"}


def _require_member_exists(connection, member_id: int):
    row = connection.execute(
        "SELECT id FROM members WHERE id = ?",
        (member_id,),
    ).fetchone()
    if not row:
        raise ValueError("Member could not be found.")


def _normalize_role(value: str | None) -> str:
    role = (value or "").strip()
    if role == "support":
        return "sup"
    if role not in VALID_ROLES:
        raise ValueError("Role must be one of:DPS, SUP, FLEX")
    return role


def _ensure_unique_character_name(
    connection,
    member_id: int,
    name: str,
    exclude_character_id: int | None = None,
):
    query = """
        SELECT id
        FROM characters
        WHERE member_id = ?
            AND lower(name) = lower(?)
    """
    params = [member_id, name.strip()]
    if exclude_character_id is not None:
        query += " AND id!=?"
        params.append(exclude_character_id)

    existing = connection.execute(query, tuple(params)).fetchone()
    if existing:
        raise ValueError("This member already has this character.")


def _validate_update_input(value, field_name: str) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a number")
    if parsed < 0:
        raise ValueError(f"{field_name} must be 0 or higher")

    return parsed


# Time helper
def _format_timestamp(value: str | None) -> str:
    if not value:
        return "Not tracked"

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value

    return parsed.strftime("%d %b %Y, %H:%M UTC")


def get_members_page_data():
    # Build one page payload: member rows, grouped characters, and latest sync per member.
    with get_connection() as connection:
        member_rows = connection.execute(
            "SELECT * FROM members ORDER BY display_name ASC"
        ).fetchall()
        character_rows = connection.execute(
            "SELECT * FROM characters ORDER BY item_level DESC, name ASC"
        ).fetchall()
    members = []
    for row in member_rows:
        member = dict(row)
        member["created_at_formatted"] = _format_timestamp(member.get("created_at"))
        members.append(member)
    characters = [dict(row) for row in character_rows]

    characters_by_member = {}
    latest_sync_by_member = {}

    for character in characters:
        member_id = character["member_id"]
        characters_by_member.setdefault(member_id, []).append(character)
        last_synced_at = character.get("last_synced_at")
        if last_synced_at and (
            member_id not in latest_sync_by_member
            or last_synced_at > latest_sync_by_member[member_id]
        ):
            latest_sync_by_member[member_id] = last_synced_at

    latest_sync_by_member = {
        member_id: _format_timestamp(timestamp)
        for member_id, timestamp in latest_sync_by_member.items()
    }

    return {
        "members": members,
        "characters_by_member": characters_by_member,
        "latest_sync_by_member": latest_sync_by_member,
    }


def create_member_record(
    display_name: str,
    discord_name: str,
    region: str,
    world: str,
    roster_name: str,
    notes: str,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO members (
                display_name,
                discord_name,
                region,
                world,
                roster_name,
                notes,
                created_at
            )
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                display_name,
                discord_name,
                region,
                world,
                roster_name,
                notes,
                current_timestamp(),
            ),
        )


def save_member_roster(member_id: int, roster_data: dict):
    # Thin service wrapper kept for UI/service boundary consistency.
    save_imported_roster(member_id, roster_data)


def prepare_member_refresh(member_id: int) -> tuple[str, str]:
    # Validate required refresh context and return normalized search inputs.
    with get_connection() as connection:
        member_row = connection.execute(
            "SELECT id, region, roster_name FROM members WHERE id = ?",
            (member_id,),
        ).fetchone()

    if member_row is None:
        raise ValueError("Member could not be found for refresh.")

    member = dict(member_row)
    region = (member.get("region") or "").strip()
    roster_name = (member.get("roster_name") or "").strip()
    if not region or not roster_name:
        raise ValueError(
            "This member needs a saved region and roster name before it can be refreshed."
        )
    return region, roster_name


def prepare_refresh_roster(results: list, roster_name: str) -> dict:
    # Prefer exact roster-name match; fall back to first candidate when no exact match exists.
    if not results:
        raise ValueError("No matching roster could be found for this member refresh.")
    normalized_roster_name = roster_name.strip().casefold()

    for result in results:
        matched_name = (result.matched_character_name or "").strip().casefold()
        if matched_name == normalized_roster_name:
            return asdict(result)

    return asdict(results[0])


async def create_character_record(member_id: int, character_name: str):
    with get_connection() as connection:
        member_row = connection.execute(
            "SELECT * FROM members WHERE id= ?",
            (member_id,),
        ).fetchone()
        if member_row is None:
            raise ValueError("Member could not be found.")

        member = dict(member_row)

        region = member["region"]

        results = await search_member_rosters(region, character_name, "")

        if not results:
            raise ValueError("No matching character found.")

        selected = results[0]

        name = (selected.matched_character_name or "").strip()
        class_name = (selected.matched_character_class or "").strip() or "Unknown"
        item_level = selected.matched_character_item_level
        combat_role = _normalize_role(selected.matched_character_combat_role)
        combat_power_score = selected.matched_character_combat_power
        region = (selected.matched_character_region or region).strip()
        world = (selected.matched_character_server_name or "").strip()
        combat_power_id = selected.matched_character_combat_power_id
        source = "lostark_bible"

        _ensure_unique_character_name(connection, member_id, name)
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
                name,
                class_name,
                item_level,
                combat_power_id,
                combat_role,
                combat_power_score,
                region,
                world,
                1,
                source,
                current_timestamp(),
            ),
        )
        connection.commit()

async def refresh_character_record(member_id: int, character_id:int):

    with get_connection() as connection:
        character_row = connection.execute(
            "SELECT * FROM characters WHERE id= ? AND member_id = ?",
            (character_id,member_id,),
        ).fetchone()
        if character_row is None:
            raise ValueError("Character could not be found.")

        character = dict(character_row)

        region = character["region"]
        character_name = character["name"]

        results = await search_member_rosters(region, character_name, "")

        if not results:
            raise ValueError("No matching character found for refresh.")

        target = (character_name or "").strip().casefold()
        exact = [
            r for r in results
            if (r.matched_character_name or "").strip().casefold() == target
        ]
        selected = exact[0] if exact else results[0]

        class_name = (selected.matched_character_class or "").strip() or "Unknown"
        item_level = selected.matched_character_item_level
        combat_power_id = selected.matched_character_combat_power_id
        combat_role = _normalize_role(selected.matched_character_combat_role)
        combat_power_score = selected.matched_character_combat_power
        new_region = (selected.matched_character_region or region or "").strip()
        world = (selected.matched_character_server_name or "").strip()

        connection.execute(
            """
            UPDATE characters
            SET class_name = ?,
                item_level = ?,
                combat_power_id = ?,
                combat_role = ?,
                combat_power_score = ?,
                region = ?,
                world = ?,
                last_synced_at = ?
            WHERE id = ? AND member_id = ?
            """,
            (
                class_name,
                item_level,
                combat_power_id,
                combat_role,
                combat_power_score,
                new_region,
                world,
                current_timestamp(),
                character_id,
                member_id,
            ),
        )
        connection.commit()
    

def update_member_character(
    character_id: int, member_id: int, combat_role: str, combat_power_score
):
    with get_connection() as connection:
        _require_member_exists(connection, member_id)
        normalize_role = _normalize_role(combat_role)
        normalized_power = _validate_update_input(combat_power_score, "Combat Power")

        query = """
                UPDATE characters
                SET combat_role = ?, combat_power_score = ?
                WHERE id = ? AND member_id = ?
        """
        params = (normalize_role, normalized_power, character_id, member_id)

        connection.execute(query, tuple(params))
        connection.commit()


def force_delete_member_record(member_id: int):
    delete_member(member_id)


def force_delete_character_record(member_id: int, character_id: int):
    delete_character(member_id, character_id)
