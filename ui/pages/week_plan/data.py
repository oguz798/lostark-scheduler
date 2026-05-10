from app.domain.days import DAY_ORDER
from app.schemas.week_plan import (
    CharacterPoolMember,
    PlanAssignment,
    PlanCharacter,
    PlanGroup,
    PlanRaidBlock,
    ScheduleRow,
    WeekPlanContext,
)


def build_week_plan_context(
    page_data: dict, member_availability_rows: list[dict]
) -> WeekPlanContext:

    character_pool = _build_character_pool(page_data)
    raid_blocks = _build_raid_blocks(page_data)
    schedule_rows = _build_schedule_rows(raid_blocks)

    characters_by_id = {
        character.id: character
        for member_data in character_pool.values()
        for character in member_data.characters
    }

    groups_by_id = {
        group_data.raid_group_id: group_data
        for raid_data in raid_blocks.values()
        for group_data in raid_data.groups.values()
    }

    member_availability_by_id = {
        member_availability["member_id"]: member_availability
        for member_availability in member_availability_rows
    }

    assignments_by_id = {}
    assignments_by_group_slot = {}

    for group_data in groups_by_id.values():
        for party_slots in group_data.parties.values():
            for assignment in party_slots:
                if assignment is None:
                    continue

                assignments_by_id[assignment.assignment_id] = assignment
                assignments_by_group_slot[
                    (assignment.raid_group_id, assignment.slot_order)
                ] = assignment

    return WeekPlanContext(
        week=page_data["week"],
        raids=page_data["raids"],
        character_pool=character_pool,
        raid_blocks=raid_blocks,
        schedule_rows=schedule_rows,
        member_availability_rows=member_availability_rows,
        characters_by_id=characters_by_id,
        groups_by_id=groups_by_id,
        member_availability_by_id=member_availability_by_id,
        assignments_by_id=assignments_by_id,
        assignments_by_group_slot=assignments_by_group_slot,
    )


def _build_character_pool(
    page_data: dict,
) -> dict[int, CharacterPoolMember]:
    character_pool: dict[int, CharacterPoolMember] = {}

    for character_row in page_data["characters"]:
        member_id = character_row["member_id"]
        member_name = character_row.get("member_name") or f"Member {member_id}"

        if member_id not in character_pool:
            character_pool[member_id] = CharacterPoolMember(
                member_id=member_id,
                member_name=member_name,
            )

        character_pool[member_id].characters.append(
            PlanCharacter(
                id=character_row["id"],
                member_id=member_id,
                member_name=member_name,
                name=character_row["name"],
                class_name=character_row["class_name"],
                item_level=character_row.get("item_level"),
                combat_role=character_row.get("combat_role"),
                combat_power_score=character_row.get("combat_power_score"),
                is_active=bool(character_row.get("is_active")),
            )
        )

    for member_data in character_pool.values():
        member_data.characters.sort(
            key=lambda character: float(character.item_level or 0),
            reverse=True,
        )

    return character_pool


def _build_raid_blocks(page_data: dict) -> dict[str, PlanRaidBlock]:
    assignments_by_raid_group_id = _group_assignments_by_raid_group_id(
        page_data["raid_assignments"]
    )
    raid_blocks = _build_empty_raid_blocks(page_data["raids"])

    for raid_group in page_data["raid_groups"]:
        raid_name = f"{raid_group['raid_title']} {raid_group['raid_difficulty']}"
        group_name = f"Group {raid_group['group_number']}"
        player_count = int(raid_group.get("player_count") or 0)

        if raid_name not in raid_blocks:
            raid_blocks[raid_name] = PlanRaidBlock(
                raid_id=raid_group["raid_id"],
                min_item_level=float(raid_group.get("min_item_level") or 0),
            )

        raid_blocks[raid_name].groups[group_name] = PlanGroup(
            raid_group_id=raid_group["id"],
            raid_id=raid_group["raid_id"],
            group_number=int(raid_group["group_number"]),
            day=raid_group.get("day") or "",
            start_time=raid_group.get("start_time"),
            sort_order=int(raid_group.get("sort_order") or 0),
            notes=raid_group.get("notes") or "",
            parties=_build_group_parties(
                assignments_by_raid_group_id.get(raid_group["id"], []),
                player_count,
            ),
        )

    return raid_blocks


def _build_group_parties(
    assignments: list[dict],
    player_count: int,
) -> dict[str, list[PlanAssignment | None]]:
    # Slots are fixed-position lists to keep drop/swap logic index-based.
    parties: dict[str, list[PlanAssignment | None]] = {
        "P1": [None, None, None, None],
    }

    if player_count == 8:
        parties["P2"] = [None, None, None, None]

    for assignment_row in assignments:
        slot_order = int(assignment_row["slot_order"] or 0)

        if slot_order <= 0:
            continue

        plan_assignment = PlanAssignment(
            assignment_id=assignment_row["id"],
            raid_group_id=assignment_row["raid_group_id"],
            character_id=assignment_row["character_id"],
            member_id=assignment_row["member_id"],
            slot_order=slot_order,
            character_name=assignment_row["character_name"],
            class_name=assignment_row["class_name"],
            member_name=assignment_row["member_name"],
            combat_role=assignment_row["combat_role"],
            item_level=assignment_row["item_level"],
            combat_power_score=assignment_row["combat_power_score"],
        )

        if slot_order <= 4:
            parties["P1"][slot_order - 1] = plan_assignment
        elif player_count == 8 and slot_order <= 8:
            parties["P2"][slot_order - 5] = plan_assignment

    return parties


def _build_schedule_rows(
    raid_blocks: dict[str, PlanRaidBlock],
) -> list[ScheduleRow]:
    schedule_rows = []

    for raid_name, raid_data in raid_blocks.items():
        for group_data in raid_data.groups.values():
            day = group_data.day
            start_time = group_data.start_time
            group_number = group_data.group_number

            if start_time:
                time_text = start_time
            elif day:
                time_text = "after"
            else:
                time_text = "unscheduled"

            # Keep a deterministic order for weekly schedule rendering.
            sort_key = (
                DAY_ORDER.get(day, 99),
                int(group_data.sort_order or 0),
                start_time or "99:99",
                raid_name,
                group_number,
            )
            schedule_rows.append(
                (
                    sort_key,
                    ScheduleRow(
                        day=day or "-",
                        time_text=time_text,
                        raid_text=f"{raid_name} Group {group_number}",
                        notes=group_data.notes or "",
                    ),
                )
            )

    schedule_rows.sort(key=lambda row: row[0])
    return [visible_row for _sort_key, visible_row in schedule_rows]


def build_eligible_character_pool(
    context: WeekPlanContext,
    raid_data: PlanRaidBlock,
    filters: dict,
) -> tuple[list[tuple[CharacterPoolMember, list[PlanCharacter]]], set[int]]:
    min_item_level = raid_data.min_item_level
    query = (filters["search_query"] or "").strip().lower()
    role_filter = (filters["role_filter"] or "ALL").upper()
    show_assigned = bool(filters["show_assigned"])
    assigned_ids = _get_assigned_character_ids(context, raid_data)

    eligible_members = []

    for member_data in context.character_pool.values():
        eligible_characters = []

        for character in member_data.characters:
            if float(character.item_level or 0) < min_item_level:
                continue

            if not show_assigned and int(character.id) in assigned_ids:
                continue

            if query and not _matches_character_query(character, query):
                continue

            if not _matches_role_filter(character, role_filter):
                continue

            eligible_characters.append(character)

        if eligible_characters:
            eligible_members.append((member_data, eligible_characters))

    return eligible_members, assigned_ids


def format_availability_cell(day_availability: dict) -> str:
    status = (day_availability.get("status") or "available").lower()
    available_after = day_availability.get("available_after") or ""

    if status == "available":
        return "free"

    if status == "unavailable":
        return "-"

    if status == "after":
        return f">{_format_time_12h(available_after)}" if available_after else "after"

    return status


def _format_time_12h(value: str) -> str:
    hour_text, minute_text = value.split(":")
    hour = int(hour_text)
    minute = int(minute_text)

    suffix = "am" if hour < 12 else "pm"
    display_hour = hour % 12 or 12

    if minute == 0:
        return f"{display_hour}{suffix}"

    return f"{display_hour}:{minute:02d}{suffix}"


def build_group_schedule_draft(group_data: PlanGroup) -> dict[str, str | int]:
    return {
        "day": group_data.day or "Wed",
        "start_time": group_data.start_time or "",
        "sort_order": group_data.sort_order or group_data.group_number,
    }


def get_next_group_number(groups: dict[str, PlanGroup]) -> int:
    if not groups:
        return 1

    group_numbers = [int(group_data.group_number) for group_data in groups.values()]
    return max(group_numbers) + 1


def _build_empty_raid_blocks(raids: list[dict]) -> dict[str, PlanRaidBlock]:
    raid_blocks: dict[str, PlanRaidBlock] = {}

    for raid in raids:
        raid_name = f"{raid['title']} {raid['difficulty']}"
        raid_blocks[raid_name] = PlanRaidBlock(
            raid_id=raid["id"],
            min_item_level=float(raid.get("min_item_level") or 0),
        )

    return raid_blocks


def _group_assignments_by_raid_group_id(
    assignments: list[dict],
) -> dict[int, list[dict]]:
    assignments_by_raid_group_id: dict[int, list[dict]] = {}

    for assignment_row in assignments:
        raid_group_id = assignment_row["raid_group_id"]
        assignments_by_raid_group_id.setdefault(raid_group_id, []).append(
            assignment_row
        )

    return assignments_by_raid_group_id


def _get_assigned_character_ids(
    context: WeekPlanContext, raid_data: PlanRaidBlock
) -> set[int]:

    raid_group_ids = {group.raid_group_id for group in raid_data.groups.values()}

    return {
        assignment.character_id
        for assignment in context.assignments_by_id.values()
        if assignment.raid_group_id in raid_group_ids
    }


def _matches_character_query(character: PlanCharacter, query: str) -> bool:
    name = (character.name or "").lower()
    class_name = (character.class_name or "").lower()
    return query in name or query in class_name


def _matches_role_filter(character: PlanCharacter, role_filter: str) -> bool:
    role = (character.combat_role or "").upper()

    if role_filter == "DPS":
        return role == "DPS"

    if role_filter == "SUP":
        return role in ("SUP", "SUPPORT")

    return True
