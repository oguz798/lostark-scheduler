from app.domain.roles import get_required_slot_role, normalize_combat_role
from app.schemas.week_plan import (
    PlanGroup,
    WeekPlanContext,
    PlanAssignment,
    PlanCharacter,
)


def _get_member_ids_for_group(
    context: WeekPlanContext,
    target_group: PlanGroup,
    exclude_assignment_id: int | None = None,
) -> list[int]:
    member_ids = []

    for assignment in context.assignments_by_id.values():
        if assignment.raid_group_id != target_group.raid_group_id:
            continue

        if (
            exclude_assignment_id is not None
            and assignment.assignment_id == exclude_assignment_id
        ):
            continue

        member_ids.append(assignment.member_id)

    return member_ids


def _validate_member_can_join_group(
    character: PlanCharacter,
    target_group: PlanGroup,
    context: WeekPlanContext,
    exclude_assignment_id: int | None = None,
) -> tuple[bool, str]:
    target_member_ids = _get_member_ids_for_group(
        context,
        target_group,
        exclude_assignment_id=exclude_assignment_id,
    )

    target_member_ids.append(character.member_id)

    return validate_no_duplicate_member_ids(target_member_ids)


def validate_no_duplicate_member_ids(member_ids: list[int]) -> tuple[bool, str]:
    seen_member_ids = set()

    for member_id in member_ids:
        if member_id is None:
            continue

        if member_id in seen_member_ids:
            return False, "This member is already assigned to this group."

        seen_member_ids.add(member_id)

    return True, ""


def validate_no_duplicate_members(
    assignments: list[PlanAssignment],
) -> tuple[bool, str]:
    member_ids = [assignment.member_id for assignment in assignments]
    return validate_no_duplicate_member_ids(member_ids)


def validate_slot_role(
    character_role: str | None,
    slot_order: int,
) -> tuple[bool, str]:
    normalized_role = normalize_combat_role(character_role)
    required_role = get_required_slot_role(slot_order)

    if normalized_role != required_role:
        return False, f"Slot {slot_order} requires {required_role}."

    return True, ""


def validate_assignment_move_rules_for_context(
    character: PlanCharacter,
    target_group: PlanGroup,
    source_assignment_id: int,
    context: WeekPlanContext,
) -> tuple[bool, str]:
    return _validate_member_can_join_group(
        character,
        target_group,
        context,
        exclude_assignment_id=source_assignment_id,
    )


def validate_new_assignment_rules_for_context(
    character: PlanCharacter,
    target_group: PlanGroup,
    context: WeekPlanContext,
) -> tuple[bool, str]:
    ok, message = _validate_member_can_join_group(
        character,
        target_group,
        context,
    )
    if not ok:
        return ok, message

    character_raid_ids = {
        context.groups_by_id[assignment.raid_group_id].raid_id
        for assignment in context.assignments_by_id.values()
        if assignment.character_id == character.id
    }

    if target_group.raid_id in character_raid_ids:
        return False, "Character already assigned to this raid this week."

    if len(character_raid_ids) >= 3:
        return False, "Character reached weekly raid limit (3)."

    return True, ""


def validate_assignment_swap_rules(
    source_group: PlanGroup,
    target_group: PlanGroup,
    source_assignment: PlanAssignment,
    target_assignment: PlanAssignment,
) -> tuple[bool, str]:
    ok, message = validate_slot_role(
        source_assignment.combat_role,
        target_assignment.slot_order,
    )
    if not ok:
        return ok, message

    ok, message = validate_slot_role(
        target_assignment.combat_role, source_assignment.slot_order
    )
    if not ok:
        return ok, message

    if source_group.raid_group_id == target_group.raid_group_id:
        return True, ""

    source_replacements = {source_assignment.slot_order: target_assignment}
    target_replacements = {target_assignment.slot_order: source_assignment}

    target_final_assignments = _build_final_assignments(
        target_group,
        target_replacements,
    )
    ok, message = validate_no_duplicate_members(target_final_assignments)
    if not ok:
        return ok, message

    source_final_assignments = _build_final_assignments(
        source_group,
        source_replacements,
    )
    ok, message = validate_no_duplicate_members(source_final_assignments)
    if not ok:
        return ok, message

    return True, ""


def _build_final_assignments(
    group: PlanGroup,
    replacements: dict[int, PlanAssignment],
) -> list[PlanAssignment]:
    final_assignments = []

    for party_slots in group.parties.values():
        for assignment in party_slots:
            if assignment is None:
                continue

            final_assignments.append(
                replacements.get(assignment.slot_order, assignment)
            )

    return final_assignments
