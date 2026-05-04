from nicegui import ui

from app.services.weeks_service import (
    create_assignment_record,
    create_scheduled_raid_record,
    get_week_detail_page_data,
    delete_assignment_record,
    swap_assignments_by_slot,
)
from ui.components.layout import app_shell


# 1) Build Helpers (pure transforms)
def build_filtered_pool(characters, assigned_ids, filters) -> dict:

    query = (filters["search_query"] or "").strip().lower()
    selected_role = (filters["role_filter"] or "ALL").upper()

    grouped = {}
    for c in characters:
        char_id = int(c.get("id") or 0)
        name = c.get("name") or ""
        class_name = c.get("class_name") or ""
        role = (c.get("combat_role") or "").upper()

        if not filters["show_assigned"] and char_id in assigned_ids:
            continue
        if query and query not in name.lower() and query not in class_name.lower():
            continue
        if selected_role == "DPS" and role != "DPS":
            continue
        if selected_role == "SUP" and role not in ("SUP", "SUPPORT"):
            continue

        grouped.setdefault(c.get("member_id"), []).append(c)
    return grouped


def build_parties(raid_assignments, player_count):

    parties = {1: []}
    if player_count == 8:
        parties[2] = []

    for a in raid_assignments:
        slot = int(a.get("slot_order") or 0)
        if player_count == 8 and slot >= 5:
            parties[2].append(a)
        else:
            parties[1].append(a)

    return parties


def build_raid_assignments(all_assignments, scheduled_raid_id):

    raid_assignments = []
    assigned_ids = set()
    for assignment in all_assignments:
        if assignment["scheduled_raid_id"] == scheduled_raid_id:
            raid_assignments.append(assignment)
            assigned_ids.add(int(assignment["character_id"]))

    return (raid_assignments, assigned_ids)


def build_week_assignment_context(page_data):
    scheduled_raids = page_data["scheduled_raids"]
    all_assignments = page_data["scheduled_raid_assignments"]
    raid_def_by_scheduled = {
        int(r["id"]): int(r["raid_definition_id"]) for r in scheduled_raids
    }
    return scheduled_raids, all_assignments, raid_def_by_scheduled


# 2) Validation/Rules (pure checks)
def check_party_add(role, slot_order, parties, player_count):
    normalized_role = (role or "").upper()

    # Decide target party by slot
    if slot_order <= 4:
        party_no = 1
    else:
        party_no = 2
    party = parties.get(party_no, [])

    size = len(party)
    dps_count = 0
    sup_count = 0
    for a in party:
        r = (a.get("combat_role") or "").upper()
        if r == "DPS":
            dps_count += 1
        elif r in ("SUP", "SUPPORT"):
            sup_count += 1

    counts = {"size": size, "dps": dps_count, "sup": sup_count}

    # Party full
    if size >= 4:
        return False, "Party is full.", party_no, counts

    # Role-based limits: 3 DPS + 1 SUP
    if normalized_role in ("SUP", "SUPPORT") and sup_count >= 1:
        return False, "Support slot is full in this party.", party_no, counts

    if normalized_role == "DPS" and dps_count >= 3:
        return False, "DPS slots are full in this party.", party_no, counts

    return True, "", party_no, counts


def validate_assignment_limits(
    character_id, scheduled_raid_id, scheduled_raids, all_assignments, characters
):

    raid_def_by_scheduled = {
        int(r["id"]): int(r["raid_definition_id"]) for r in scheduled_raids
    }
    character_to_member = {int(c["id"]): int(c["member_id"]) for c in characters}

    target_scheduled_id = int(scheduled_raid_id)
    target_raid_def_id = raid_def_by_scheduled.get(target_scheduled_id)

    target_character_id = int(character_id)
    member_id = character_to_member.get(target_character_id)

    if member_id is None:
        return False, "Character/member could not be resolved."

    if target_raid_def_id is None:
        return False, "Target raid could not be resolved."

    # Block if this member already has any character in this scheduled raid
    for assignment in all_assignments:
        if int(assignment["scheduled_raid_id"]) != target_scheduled_id:
            continue

        assigned_character_id = int(assignment["character_id"])
        assigned_member_id = character_to_member.get(assigned_character_id)
        if assigned_member_id == member_id:
            return False, "This member is already assigned to this raid."

    char_week_assignments = [
        a for a in all_assignments if int(a["character_id"]) == int(character_id)
    ]
    char_raid_defs = {
        raid_def_by_scheduled.get(int(a["scheduled_raid_id"]))
        for a in char_week_assignments
        if raid_def_by_scheduled.get(int(a["scheduled_raid_id"])) is not None
    }

    if target_raid_def_id in char_raid_defs:
        return False, "Character already assigned to this raid this week."

    if len(char_raid_defs) >= 3:
        return False, "Character reached weekly raid limit (3)."

    return True, ""


def validate_swap_party_rules(source_slot, target_slot, parties, player_count):
    source_slot = int(source_slot)
    target_slot = int(target_slot)

    def normalize_role(value):
        role = (value or "").upper()
        if role == "SUPPORT":
            return "SUP"
        return role

    # Build slot -> assignment map from current parties
    assignment_by_slot = {}
    for assignment in parties.get(1, []):
        assignment_by_slot[int(assignment["slot_order"])] = assignment
    if int(player_count) == 8:
        for assignment in parties.get(2, []):
            assignment_by_slot[int(assignment["slot_order"])] = assignment

    source_assignment = assignment_by_slot.get(source_slot)
    target_assignment = assignment_by_slot.get(target_slot)

    if source_assignment is None or target_assignment is None:
        return False, "Swap requires both slots to be occupied."

    role_by_slot = {}
    for slot, assignment in assignment_by_slot.items():
        role_by_slot[slot] = normalize_role(assignment.get("combat_role"))

    # Simulate role swap
    source_role = role_by_slot[source_slot]
    target_role = role_by_slot[target_slot]
    role_by_slot[source_slot] = target_role
    role_by_slot[target_slot] = source_role

    def validate_party_slots(slots):
        dps_count = 0
        sup_count = 0
        for s in slots:
            role = role_by_slot.get(s)
            if role == "DPS":
                dps_count += 1
            elif role == "SUP":
                sup_count += 1
            elif role:
                return False, f"Unknown role in slot {s}: {role}"

        if dps_count > 3:
            return False, "Swap would exceed DPS limit in a party (max 3)."
        if sup_count > 1:
            return False, "Swap would exceed Support limit in a party (max 1)."
        return True, ""

    affected_party_1 = (source_slot <= 4) or (target_slot <= 4)
    affected_party_2 = int(player_count) == 8 and (
        (source_slot >= 5) or (target_slot >= 5)
    )

    if affected_party_1:
        ok, msg = validate_party_slots([1, 2, 3, 4])
        if not ok:
            return False, msg

    if affected_party_2:
        ok, msg = validate_party_slots([5, 6, 7, 8])
        if not ok:
            return False, msg

    return True, ""


# 3) Action Handlers (mutations + notify + refresh)
def remove_assignment_action(assignment, ui_state):

    try:
        delete_assignment_record(assignment["id"])
        render_raids.refresh(ui_state)
        ui.notify(
            f"{assignment['character_name']} got removed from the raid. ", color="info"
        )
    except ValueError as exc:
        ui.notify(str(exc), color="negative")


def create_assignment_action(
    ui_state,
    scheduled_raid_id,
    character_id: str | int,
    slot_order: int,
    character_role: str,
    assign_notes: str,
    scheduled_raid_assignments,
    on_success_refresh,
):
    if not character_id:
        ui.notify("Select a character", color="negative")
        return
    if slot_order is None:
        ui.notify("Raid is full.", color="negative")
        return

    exists = any(
        a["scheduled_raid_id"] == scheduled_raid_id
        and int(a["character_id"]) == int(character_id)
        for a in scheduled_raid_assignments
    )
    if exists:
        ui.notify("Character already assigned to this raid.", color="warning")
        return

    # Weekly raid-limit validation: max 3 total, all must be different raid definitions
    fresh = get_week_detail_page_data(ui_state["week_id"])
    scheduled_raids = fresh["scheduled_raids"]
    all_assignments = fresh["scheduled_raid_assignments"]
    characters = fresh["characters"]

    is_allowed, message = validate_assignment_limits(
        character_id=character_id,
        scheduled_raid_id=scheduled_raid_id,
        scheduled_raids=scheduled_raids,
        all_assignments=all_assignments,
        characters=characters,
    )
    if not is_allowed:
        ui.notify(message, color="warning")
        return

    create_assignment_record(
        scheduled_raid_id,
        int(character_id),
        int(slot_order),
        assign_notes.strip() or "",
    )
    on_success_refresh()
    ui.notify("Assignment created", color="positive")


def create_scheduled_raid_action(
    ui_state,
    raid_definition_id,
    day,
    group_number,
    start_time,
    notes,
    sort_order,
):
    if not raid_definition_id.value:
        ui.notify("Select a raid first.", color="negative")
        return

    create_scheduled_raid_record(
        ui_state["week_id"],
        int(raid_definition_id.value or 0),
        day.value or "",
        int(group_number.value or 0),
        start_time.value or None,
        notes.value.strip() or "",
        int(sort_order.value or 0),
    )
    render_raids.refresh(ui_state)
    ui.notify("Raid created.", color="positive")


def remove_scheduled_raid_action(): ...
def swap_assignment_action(ui_state, scheduled_raid_id, source_slot, target_slot):
    try:
        swap_assignments_by_slot(scheduled_raid_id, source_slot, target_slot)
        render_raids.refresh(ui_state)
        ui.notify("Swap success", color="positive")
    except ValueError as exc:
        ui.notify(str(exc), color="negative")


# 4) UI State Handlers (no DB)
def update_filter(ui_state, key, value):
    if key == "search_query":
        ui_state["filters"]["search_query"] = (value or "").strip()
    elif key == "role_filter":
        ui_state["filters"]["role_filter"] = (value or "ALL").upper()
    elif key == "show_assigned":
        ui_state["filters"]["show_assigned"] = bool(value)

    render_raids.refresh(ui_state)


def set_drag_character(ui_state, character_id, role):
    ui_state["drag"]["character_id"] = int(character_id) if character_id else None
    ui_state["drag"]["role"] = (role or "").upper()


def clear_drag_character(ui_state):
    ui_state["drag"]["character_id"] = None
    ui_state["drag"]["role"] = ""
    render_raids.refresh(ui_state)


# 5) Small Render Fragments
def render_week_sidebar(raid_definitions, ui_state):
    with ui.element("div").classes("app-panel-head"):
        ui.html("<h2>Add Scheduled Raid</h2>")
    with ui.element("div").classes("app-panel-body app-form"):
        raid_definition_id = ui.select(
            {
                str(raid["id"]): f"{raid['title']} - {raid['difficulty']}"
                for raid in raid_definitions
            },
            label="Raid",
        )
        day = ui.select(
            ["Wed", "Thu", "Fri", "Sat", "Sun"], label="Day", value="Wed"
        ).props("outlined")
        group_number = ui.number("Group Number", value=1)
        start_time = ui.input("Start Time").props("type=time")
        notes = ui.textarea("Notes")
        sort_order = ui.number("Sort Order", value=1)
        ui.button(
            "Create Raid",
            on_click=lambda: create_scheduled_raid_action(
                ui_state,
                raid_definition_id,
                day,
                group_number,
                start_time,
                notes,
                sort_order,
            ),
        ).classes("app-button-primary")


def render_character_pool(grouped, on_drag_start):

    ui.html("<h3>Character Pool</h3>")
    with ui.element("div").classes("grid gap-2 max-h-64 overflow-auto"):
        for member_id in sorted(grouped.keys(), key=lambda x: int(x or 0)):
            member_chars = sorted(
                grouped[member_id],
                key=lambda c: float(c.get("item_level") or 0),
                reverse=True,
            )
            member_name = member_chars[0].get("member_name") or f"Member {member_id}"
            with ui.expansion(
                f"{member_name} ({len(member_chars)})", value=False
            ).classes("w-full"):
                with ui.element("div").classes("grid gap-2"):
                    for character in member_chars:
                        with (
                            ui.element("div")
                            .classes("app-panel min-h-[52px] cursor-grab")
                            .props("draggable=true") as drag_row
                        ):
                            with ui.element("div").classes("app-panel-body py-2"):
                                role = (character.get("combat_role") or "-").upper()
                                ui.label(
                                    f"{character['name']} - {character['class_name']} · {role}"
                                )
                        drag_row.on(
                            "dragstart",
                            lambda _e, cid=character["id"], character_role=character["combat_role"]: (
                                on_drag_start(cid, character_role)
                            ),
                        )


def render_party_slots(parties, player_count, handle_drop, ui_state):

    ui.html("<h3>Party 1 Slots</h3>")
    with ui.element("div").classes(
        "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2"
    ):
        for slot in range(1, 5):
            assigned = None
            for assignment in parties[1]:
                if int(assignment["slot_order"]) == slot:
                    assigned = assignment
                    break
            with ui.element("div").classes("app-panel min-h-[88px]") as slot_cell:
                with ui.element("div").classes("app-panel-body py-2"):
                    ui.label(f"Slot {slot}")
                    if assigned:
                        with (
                            ui.element("div")
                            .classes("cursor-grab")
                            .props("draggable=true") as assigned_drag
                        ):
                            role = (assigned.get("combat_role") or "-").upper()
                            ui.label(
                                f"{assigned['character_name']} - {assigned['class_name']} · {role}"
                            )
                            ui.button(
                                icon="delete",
                                on_click=lambda _e, a=assigned: (
                                    remove_assignment_action(
                                        a,
                                        ui_state,
                                    )
                                ),
                            ).classes("app-icon-btn app-icon-btn-danger")
                        assigned_drag.on(
                            "dragstart",
                            lambda _e, cid=assigned["character_id"], r=assigned["combat_role"]: (
                                set_drag_character(ui_state, cid, r)
                            ),
                        )
                    else:
                        ui.html('<div class="app-muted">Drop character here</div>')

            slot_cell.on("dragover.prevent", lambda: None)
            slot_cell.on("drop", lambda _e, s=slot: handle_drop(s))

    if player_count == 8:
        ui.html("<h3>Party 2 Slots</h3>")
        with ui.element("div").style(
            "display:grid; grid-template-columns:repeat(4, 1fr); gap:8px;"
        ):
            for slot in range(5, 9):
                assigned = None
                for assignment in parties[2]:
                    if int(assignment["slot_order"]) == slot:
                        assigned = assignment
                        break
                with ui.element("div").classes("app-panel min-h-[72px]") as slot_cell:
                    with ui.element("div").classes("app-panel-body"):
                        ui.label(f"Slot {slot}")
                        if assigned:
                            with (
                                ui.element("div")
                                .classes("cursor-grab")
                                .props("draggable=true") as assigned_drag
                            ):
                                role = (assigned.get("combat_role") or "-").upper()
                                ui.label(
                                    f"{assigned['character_name']} - {assigned['class_name']} · {role}"
                                )
                                ui.button(
                                    icon="delete",
                                    on_click=lambda _e, a=assigned: (
                                        remove_assignment_action(a, ui_state)
                                    ),
                                ).classes("app-icon-btn app-icon-btn-danger")

                            assigned_drag.on(
                                "dragstart",
                                lambda _e, cid=assigned["character_id"], r=assigned["combat_role"]: (
                                    set_drag_character(ui_state, cid, r)
                                ),
                            )
                        else:
                            ui.html('<div class="app-muted">Drop character here</div>')
                slot_cell.on("dragover.prevent", lambda: None)
                slot_cell.on("drop", lambda _e, s=slot: handle_drop(s))


def render_pool_and_forms(raid, page_data, ui_state):

    all_assignments = page_data["scheduled_raid_assignments"]
    characters = page_data["characters"]

    raid_assignments, assigned_ids = build_raid_assignments(all_assignments, raid["id"])

    grouped = build_filtered_pool(characters, assigned_ids, ui_state["filters"])
    player_count = int(raid.get("player_count") or 0)
    parties = build_parties(raid_assignments, player_count)

    def on_drag_start(character_id: int, character_role: str):
        set_drag_character(ui_state, character_id, character_role)

    def handle_drop(slot_order: int):
        cid = ui_state["drag"]["character_id"]
        character_role = ui_state["drag"]["role"]
        print(f"[drop] raid_id={raid['id']} incoming_cid={cid} incoming_role={character_role} target_slot={slot_order}")

        if not cid:
            return

        target_assignment = next(
            (a for a in raid_assignments if int(a["slot_order"]) == int(slot_order)),
            None,
        )
        source_assignment = next(
            (a for a in raid_assignments if int(a["character_id"]) == int(cid)),
            None,
        )
        source_slot = (
            int(source_assignment["slot_order"]) if source_assignment else None
        )
        print(
            "[drop] resolved "
            f"target_exists={target_assignment is not None} "
            f"target_char_id={target_assignment['character_id'] if target_assignment else None} "
            f"source_exists={source_assignment is not None} "
            f"source_slot={source_slot}"
        )

        if not target_assignment:
            allowed, reason, _, _ = check_party_add(
                character_role, slot_order, parties, player_count
            )

            if not allowed:
                ui.notify(reason, color="warning")
                return
            print("[drop] branch=create")

            create_assignment_action(
                ui_state,
                scheduled_raid_id=raid["id"],
                character_id=cid,
                slot_order=slot_order,
                character_role=character_role,
                assign_notes="",
                scheduled_raid_assignments=all_assignments,
                on_success_refresh=lambda: render_raids.refresh(ui_state),
            )
        else:
            if source_slot is not None:
                print("[drop] branch=swap_validate")

                ok, msg = validate_swap_party_rules(
                    source_slot, slot_order, parties, player_count
                )
                print(f"[drop] swap_validation ok={ok} msg='{msg}'")

                if not ok:
                    ui.notify(msg, color="negative")
                    return
                print(f"[drop] branch=swap_execute source_slot={source_slot} target_slot={slot_order}")
                swap_assignment_action(ui_state, raid["id"], source_slot, slot_order)
                return
            else:
                print("[drop] branch=occupied_blocked")

                ui.notify("Target slot is occupied.", color="negative")
        print("[drop] done -> clearing drag state")

        

    with ui.element("div").classes("app-split"):
        with ui.element("div"):
            render_character_pool(grouped, on_drag_start)
        with ui.element("div"):
            render_party_slots(
                parties,
                player_count,
                handle_drop,
                ui_state,
            )


# 6) Mid-level Render Orchestration
def render_assignments(raid, page_data, ui_state):

    filters = ui_state["filters"]
    is_open = raid["id"] in ui_state["expanded_assignments"]
    with ui.expansion("Show Assignments", value=is_open).classes("w-full") as exp:

        def on_assignment_expand_change(e, raid_id=raid["id"]):
            if bool(e.value):
                ui_state["expanded_assignments"].add(raid_id)
            else:
                ui_state["expanded_assignments"].discard(raid_id)

        exp.on_value_change(on_assignment_expand_change)
        with ui.row().classes("items-end gap-3 w-full"):
            search_text = ui.input("Search", value=filters["search_query"]).classes(
                "min-w-[260px] flex-1"
            )
            role_filter = ui.select(
                ["ALL", "DPS", "SUP"], value=filters["role_filter"], label="Role"
            ).classes("w-32")
            show_assigned = ui.checkbox(
                "Show assigned", value=filters["show_assigned"]
            ).classes("pt-2")
        # Drag source state in this local renderer

        search_text.on(
            "update:model-value",
            lambda e: update_filter(ui_state, "search_query", e.args),
        )

        role_filter.on_value_change(
            lambda e: update_filter(ui_state, "role_filter", e.value),
        )

        role_filter.props("dense outlined").classes("w-32")

        show_assigned.on(
            "update:model-value",
            lambda e: update_filter(ui_state, "show_assigned", e.args),
        )
        render_pool_and_forms(raid, page_data, ui_state)


# 7) Main Refresh Boundary
@ui.refreshable
def render_raids(ui_state):
    try:
        page_data = get_week_detail_page_data(ui_state["week_id"])
    except ValueError as exc:
        with app_shell("Week Detail"):
            with ui.element("div").classes("app-panel"):
                with ui.element("div").classes("app-panel-body"):
                    ui.label(str(exc))
        return

    if not page_data["day_groups"]:
        with ui.element("div").classes("app-panel"):
            with ui.element("div").classes("app-panel-body"):
                ui.label("No scheduled raids yet.")
        return

    for day_group in page_data["day_groups"]:
        with ui.element("div").classes("app-panel"):
            with ui.element("div").classes("app-panel-head"):
                ui.html(f"<h2>{day_group['day']}</h2>")

            with ui.element("div").classes("app-panel-body"):
                for raid in day_group["raids"]:
                    with ui.element("div").classes("app-panel"):
                        with ui.element("div").classes("app-panel-head"):
                            ui.html(
                                f"<h3>{raid['raid_title']} - {raid['raid_difficulty']} · Group {raid['group_number']}</h3>"
                            )

                        with ui.element("div").classes("app-panel-body"):
                            time_text = raid.get("start_time") or "No start time"
                            ui.label(f"{raid['day']} - {time_text}")
                            ui.label(f"Order {raid['sort_order']}")
                            ui.html(
                                f'<div class="app-muted">{raid.get("notes") or "No notes"}</div>'
                            )
                            render_assignments(raid, page_data, ui_state)


# 8) Page Entry
@ui.page("/weeks/{week_id}")
def week_detail_page(week_id: str):

    ui_state = {
        "filters": {
            "search_query": "",
            "role_filter": "ALL",
            "show_assigned": False,
        },
        "drag": {
            "character_id": None,
            "role": "",
        },
        "scheduled_raid_edit": {
            "raid_id": None,
            "notes": "",
        },
        "delete_scheduled_raid_id": None,
        "expanded_assignments": set(),  # scheduled_raid_id values
    }

    ui_state["week_id"] = int(week_id)

    try:
        page_data = get_week_detail_page_data(ui_state["week_id"])
    except ValueError as exc:
        with app_shell("Week Detail"):
            with ui.element("div").classes("app-panel"):
                with ui.element("div").classes("app-panel-body"):
                    ui.label(str(exc))
        return

    week = page_data["week"]
    raid_definitions = page_data["raid_definitions"]

    with app_shell(
        f"Week Beginning {week['start_date']}",
        week.get("notes") or "Build and review the weekly raid schedule.",
    ):
        with ui.element("div").classes("app-split"):
            with ui.element("div"):
                with ui.element("div").classes("app-panel"):
                    render_week_sidebar(raid_definitions, ui_state)
            with ui.element("div"):
                render_raids(ui_state)
