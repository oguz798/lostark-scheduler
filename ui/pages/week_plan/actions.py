from nicegui import ui

from app.schemas.week_plan import (
    PlanAssignment,
    PlanCharacter,
    PlanGroup,
    PlanRaidBlock,
    WeekPlanContext,
)
from app.services.weeks_service import (
    create_assignment_record,
    create_raid_group_record,
    delete_assignment_record,
    delete_raid_group_record,
    get_week_detail_page_data,
    move_assignment_to_slot,
    swap_assignments_by_slot,
    update_raid_group_schedule_record,
)
from app.services.availability_service import (
    fetch_week_member_availability,
    update_week_member_availability,
)
from app.domain.assignment_rules import (
    validate_new_assignment_rules_for_context,
    validate_slot_role,
    validate_assignment_swap_rules,
    validate_assignment_move_rules_for_context,
)
from app.domain.availability_rules import check_availability_for_group_time
from ui.pages.week_plan.data import (
    build_group_schedule_draft,
    build_week_plan_context,
    get_next_group_number,
)

def _build_current_context(week_id: int) -> WeekPlanContext:
    member_availability_rows = fetch_week_member_availability(week_id)
    page_data = get_week_detail_page_data(week_id)
    return build_week_plan_context(page_data, member_availability_rows)


def start_availability_edit(
    availability_data: dict,
    ui_state: dict,
    refresh_week,
) -> None:
    ui_state["editing_availability"] = {
        "member_id": availability_data["member_id"],
        "day": availability_data["day"],
    }
    ui_state["availability_draft"] = {
        "status": availability_data["status"],
        "available_after": availability_data["available_after"],
        "notes": availability_data["notes"],
    }

    refresh_week(ui_state)


def cancel_availability_edit(
    availability_data: dict,
    ui_state: dict,
    refresh_week,
) -> None:
    ui_state["editing_availability"] = None
    ui_state["availability_draft"] = {}

    refresh_week(ui_state)


def save_availability_edit(
    availability_data: dict,
    ui_state: dict,
    refresh_week,
) -> None:
    draft = ui_state["availability_draft"]
    try:
        update_week_member_availability(
            week_id=ui_state["week_id"],
            member_id=availability_data["member_id"],
            day=availability_data["day"],
            status=draft["status"],
            available_after=draft.get("available_after"),
            notes=draft.get("notes"),
        )
    except ValueError as exc:
        ui.notify(str(exc), color="negative")
        return

    ui_state["editing_availability"] = None
    ui_state["availability_draft"] = {}
    refresh_week(ui_state)
    ui.notify("Availability updated.", color="positive")


def add_raid_group_action(
    raid_data: PlanRaidBlock,
    ui_state: dict,
    refresh_week,
) -> None:
    group_number = get_next_group_number(raid_data.groups)

    create_raid_group_record(
        ui_state["week_id"],
        raid_data.raid_id,
        "Wed",
        group_number,
        None,
        "",
        group_number,
    )

    refresh_week(ui_state)
    ui.notify("Group added.", color="positive")


def delete_raid_group_action(
    group_data: PlanGroup,
    ui_state: dict,
    refresh_week,
) -> None:
    try:
        delete_raid_group_record(group_data.raid_group_id)
    except ValueError as exc:
        ui.notify(str(exc), color="negative")
        return

    refresh_week(ui_state)
    ui.notify(f"Group {group_data.group_number} removed from week.", color="positive")


def start_group_schedule_edit(
    group_data: PlanGroup,
    ui_state: dict,
    refresh_week,
) -> None:
    schedule_key = group_data.raid_group_id

    ui_state["editing_group_schedule_id"] = schedule_key
    ui_state["group_schedule_drafts"][schedule_key] = build_group_schedule_draft(
        group_data
    )

    refresh_week(ui_state)


def cancel_group_schedule_edit(
    group_data: PlanGroup,
    ui_state: dict,
    refresh_week,
) -> None:
    schedule_key = group_data.raid_group_id

    ui_state["editing_group_schedule_id"] = None
    ui_state["group_schedule_drafts"].pop(schedule_key, None)

    refresh_week(ui_state)


def update_group_schedule_action(
    group_data: PlanGroup,
    ui_state: dict,
    schedule_draft: dict,
    refresh_week,
) -> None:
    try:
        update_raid_group_schedule_record(
            group_data.raid_group_id,
            schedule_draft["day"],
            schedule_draft["start_time"],
            schedule_draft["sort_order"],
        )
    except ValueError as exc:
        ui.notify(str(exc), color="negative")
        return

    ui_state["editing_group_schedule_id"] = None
    refresh_week(ui_state)
    ui.notify("Group schedule updated.", color="positive")


def delete_assignment_action(
    assignment: PlanAssignment,
    ui_state: dict,
    refresh_week,
) -> None:
    try:
        delete_assignment_record(assignment.assignment_id)
    except ValueError as exc:
        ui.notify(str(exc), color="negative")
        return

    refresh_week(ui_state)
    ui.notify(f"{assignment.character_name} removed.", color="positive")


def toggle_assignment_drawer(
    raid_name: str,
    ui_state: dict,
    refresh_week,
) -> None:
    if ui_state["open_assignment_raid_name"] == raid_name:
        ui_state["open_assignment_raid_name"] = None
    else:
        ui_state["open_assignment_raid_name"] = raid_name

    refresh_week(ui_state)


def start_pool_character_drag(
    character: PlanCharacter,
    ui_state: dict,
) -> None:
    # Pool drag represents "new assignment intent" (no source assignment yet).
    ui_state["drag"]["character_id"] = character.id
    ui_state["drag"]["combat_role"] = character.combat_role or ""
    ui_state["drag"]["source_assignment_id"] = None
    ui_state["drag"]["source_raid_group_id"] = None
    ui_state["drag"]["source_slot_order"] = None


def start_slot_assignment_drag(
    assignment: PlanAssignment,
    ui_state: dict,
) -> None:
    # Slot drag represents "existing assignment intent" and carries source metadata for move/swap.
    ui_state["drag"]["character_id"] = assignment.character_id
    ui_state["drag"]["combat_role"] = assignment.combat_role or ""
    ui_state["drag"]["source_assignment_id"] = assignment.assignment_id
    ui_state["drag"]["source_raid_group_id"] = assignment.raid_group_id
    ui_state["drag"]["source_slot_order"] = assignment.slot_order


def clear_drag_state(ui_state: dict) -> None:
    ui_state["drag"]["character_id"] = None
    ui_state["drag"]["combat_role"] = ""
    ui_state["drag"]["source_assignment_id"] = None
    ui_state["drag"]["source_raid_group_id"] = None
    ui_state["drag"]["source_slot_order"] = None


def _notify_availability_warning(
    member_id: int,
    member_name: str,
    target_group: PlanGroup,
    context: WeekPlanContext,
) -> None:

    member_availability = context.member_availability_by_id.get(int(member_id))

    if member_availability is None:
        return

    ok, message = check_availability_for_group_time(
        member_availability["days"], target_group.day, target_group.start_time
    )

    if not ok:
        ui.notify(f"{member_name}: {message}", color="warning")


def handle_character_drop(
    target_group: PlanGroup,
    slot_order: int,
    ui_state: dict,
    refresh_week,
) -> None:
    character_id = ui_state["drag"]["character_id"]
    combat_role = ui_state["drag"]["combat_role"]
    source_assignment_id = ui_state["drag"]["source_assignment_id"]

    if not character_id:
        return

    context = _build_current_context(ui_state["week_id"])

    target_assignment = context.assignments_by_group_slot.get(
        (target_group.raid_group_id, int(slot_order))
    )

    if target_assignment:
        # Occupied target always routes through swap logic (never silently overwrite).
        _handle_assignment_swap(
            target_group,
            ui_state,
            target_assignment,
            context,
            refresh_week,
        )
        return

    allowed, reason = validate_slot_role(combat_role, slot_order)
    if not allowed:
        ui.notify(reason, color="warning")
        return

    if source_assignment_id:
        _handle_assignment_move(
            target_group, slot_order, ui_state, context, refresh_week
        )
        return

    _handle_assignment_create(target_group, slot_order, ui_state, context, refresh_week)


def _handle_assignment_swap(
    target_group: PlanGroup,
    ui_state: dict,
    target_assignment: PlanAssignment,
    context: WeekPlanContext,
    refresh_week,
) -> None:
    source_assignment_id = ui_state["drag"]["source_assignment_id"]

    if not source_assignment_id:
        ui.notify("Slot is occupied.", color="warning")
        return

    source_group = context.groups_by_id.get(
        int(ui_state["drag"]["source_raid_group_id"])
    )

    if source_group is None:
        ui.notify("Source group could not be found.", color="negative")
        return

    source_assignment = context.assignments_by_group_slot.get(
        (
            source_group.raid_group_id,
            int(ui_state["drag"]["source_slot_order"]),
        )
    )
    if source_assignment is None:
        ui.notify("Source assignment could not be found.", color="negative")
        return

    ok, message = validate_assignment_swap_rules(
        source_group,
        target_group,
        source_assignment,
        target_assignment,
    )

    if not ok:
        ui.notify(message, color="warning")
        return

    _notify_availability_warning(
        source_assignment.member_id,
        source_assignment.member_name,
        target_group,
        context,
    )

    _notify_availability_warning(
        target_assignment.member_id,
        target_assignment.member_name,
        source_group,
        context,
    )

    try:
        swap_assignments_by_slot(
            source_assignment_id,
            target_assignment.assignment_id,
        )
    except ValueError as exc:
        ui.notify(str(exc), color="negative")
        return

    clear_drag_state(ui_state)
    refresh_week(ui_state)
    ui.notify("Assignments swapped.", color="positive")


def _handle_assignment_move(
    target_group: PlanGroup,
    slot_order: int,
    ui_state: dict,
    context: WeekPlanContext,
    refresh_week,
) -> None:
    character_id = ui_state["drag"]["character_id"]
    source_assignment_id = ui_state["drag"]["source_assignment_id"]

    character = context.characters_by_id.get(int(character_id))

    if character is None:
        ui.notify("Character/member could not be resolved.", color="negative")
        return

    ok, message = validate_assignment_move_rules_for_context(
        character, target_group, source_assignment_id, context
    )

    if not ok:
        ui.notify(message, color="warning")
        return

    _notify_availability_warning(
        character.member_id, character.member_name, target_group, context
    )

    try:
        move_assignment_to_slot(
            source_assignment_id,
            target_group.raid_group_id,
            slot_order,
        )
    except ValueError as exc:
        ui.notify(str(exc), color="negative")
        return

    clear_drag_state(ui_state)
    refresh_week(ui_state)
    ui.notify("Assignment moved.", color="positive")


def _handle_assignment_create(
    target_group: PlanGroup,
    slot_order: int,
    ui_state: dict,
    context: WeekPlanContext,
    refresh_week,
) -> None:
    character_id = ui_state["drag"]["character_id"]
    character = context.characters_by_id.get(int(character_id))

    if character is None:
        ui.notify("Character/member could not be resolved.", color="negative")
        return

    is_allowed, message = validate_new_assignment_rules_for_context(
        character,
        target_group,
        context,
    )

    if not is_allowed:
        ui.notify(message, color="warning")
        return

    _notify_availability_warning(
        character.member_id, character.member_name, target_group, context
    )

    create_assignment_record(
        target_group.raid_group_id,
        character.id,
        int(slot_order),
        "",
    )

    clear_drag_state(ui_state)
    refresh_week(ui_state)
    ui.notify("Assignment created.", color="positive")
