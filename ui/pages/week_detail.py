from nicegui import ui

from app.services.weeks_service import (
    create_assignment_record,
    create_scheduled_raid_record,
    get_week_detail_page_data,
)
from ui.components.layout import app_shell


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


def render_week_sidebar(week_id, raid_definitions):
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
            on_click=lambda: create_raid_from_form(
                int(week_id),
                raid_definition_id,
                day,
                group_number,
                start_time,
                notes,
                sort_order,
            ),
        ).classes("app-button-primary")


def render_scheduled_raids(day_groups, week_id):
    for day_group in day_groups:
        with ui.element("div").classes("app-panel"):
            with ui.element("div").classes("app-panel-head"):
                ui.html(f"<h2>{day_group['day']}</h2>")

            with ui.element("div").classes("app-panel-body"):
                for raid in day_group["raids"]:
                    render_scheduled_raid_card(
                        raid,
                        week_id,
                    )


def render_assignments(raid, week_id):
    with ui.expansion("Show Assignments").classes("w-full"):
        with ui.row().classes("items-end gap-3 w-full"):
            search_text = ui.input("Search").classes("min-w-[260px] flex-1")
            role_filter = ui.select(
                ["ALL", "DPS", "SUP"], value="ALL", label="Role"
            ).classes("w-32")
            show_assigned = ui.checkbox("Show assigned", value=False).classes("pt-2")
        # Drag source state in this local renderer
        dragged_character_id = {"value": 0, "role": ""}

        @ui.refreshable
        def render_pool_and_forms():

            fresh = get_week_detail_page_data(int(week_id))
            scheduled_raid_assignments = fresh["scheduled_raid_assignments"]
            characters = fresh["characters"]

            raid_assignments = []
            assigned_ids = set()
            for assignment in scheduled_raid_assignments:
                if assignment["scheduled_raid_id"] == raid["id"]:
                    raid_assignments.append(assignment)
                    assigned_ids.add(int(assignment["character_id"]))

            query = (search_text.value or "").strip().lower()
            selected_role = (role_filter.value or "ALL").upper()

            grouped = {}
            for c in characters:
                char_id = int(c.get("id") or 0)
                name = c.get("name") or ""
                class_name = c.get("class_name") or ""
                role = (c.get("combat_role") or "").upper()

                if not show_assigned.value and char_id in assigned_ids:
                    continue
                if (
                    query
                    and query not in name.lower()
                    and query not in class_name.lower()
                ):
                    continue
                if selected_role == "DPS" and role != "DPS":
                    continue
                if selected_role == "SUP" and role not in ("SUP", "SUPPORT"):
                    continue

                grouped.setdefault(c.get("member_id"), []).append(c)

            player_count = int(raid.get("player_count") or 0)
            parties = {1: []}
            if player_count == 8:
                parties[2] = []

            for a in raid_assignments:
                slot = int(a.get("slot_order") or 0)
                if player_count == 8 and slot >= 5:
                    parties[2].append(a)
                else:
                    parties[1].append(a)

            def on_drag_start(character_id: int, character_role: str):
                dragged_character_id["value"] = character_id
                dragged_character_id["role"] = character_role

            def handle_drop(slot_order: int):
                cid = dragged_character_id["value"]
                character_role = dragged_character_id["role"]
                if not cid:
                    return
                allowed, reason, party_no, counts = check_party_add(
                    character_role, slot_order, parties, player_count
                )

                if not allowed:
                    ui.notify(reason, color="warning")
                    return

                create_assignment_from_form(
                    week_id=week_id,
                    scheduled_raid_id=raid["id"],
                    character_id=cid,
                    character_role=character_role,
                    slot_order=slot_order,
                    assign_notes="",
                    scheduled_raid_assignments=scheduled_raid_assignments,
                    on_success_refresh=render_pool_and_forms.refresh,
                )

            with ui.element("div").classes("app-split"):
                with ui.element("div"):
                    ui.html("<h3>Character Pool</h3>")
                    with ui.element("div").classes("grid gap-2 max-h-64 overflow-auto"):
                        for member_id in sorted(
                            grouped.keys(), key=lambda x: int(x or 0)
                        ):
                            member_chars = sorted(
                                grouped[member_id],
                                key=lambda c: float(c.get("item_level") or 0),
                                reverse=True,
                            )
                            member_name = (
                                member_chars[0].get("member_name")
                                or f"Member {member_id}"
                            )
                            with ui.expansion(
                                f"{member_name} ({len(member_chars)})", value=False
                            ).classes("w-full"):
                                with ui.element("div").classes("grid gap-2"):
                                    for character in member_chars:
                                        with (
                                            ui.element("div")
                                            .classes(
                                                "app-panel min-h-[52px] cursor-grab"
                                            )
                                            .props("draggable=true") as drag_row
                                        ):
                                            with ui.element("div").classes(
                                                "app-panel-body py-2"
                                            ):
                                                role = (
                                                    character.get("combat_role") or "-"
                                                ).upper()
                                                ui.label(
                                                    f"{character['name']} - {character['class_name']} · {role}"
                                                )
                                        drag_row.on(
                                            "dragstart",
                                            lambda _e, cid=character["id"], character_role=character["combat_role"]: (
                                                on_drag_start(cid, character_role)
                                            ),
                                        )
                with ui.element("div"):
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
                            with ui.element("div").classes(
                                "app-panel min-h-[88px]"
                            ) as slot_cell:
                                with ui.element("div").classes("app-panel-body py-2"):
                                    ui.label(f"Slot {slot}")
                                    if assigned:
                                        role = (
                                            assigned.get("combat_role") or "-"
                                        ).upper()
                                        ui.label(
                                            f"{assigned['character_name']} - {assigned['class_name']} · {role}"
                                        )
                                    else:
                                        ui.html(
                                            '<div class="app-muted">Drop character here</div>'
                                        )
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
                                with ui.element("div").classes(
                                    "app-panel min-h-[72px]"
                                ) as slot_cell:
                                    with ui.element("div").classes("app-panel-body"):
                                        ui.label(f"Slot {slot}")
                                        if assigned:
                                            role = (
                                                assigned.get("combat_role") or "-"
                                            ).upper()
                                            ui.label(
                                                f"{assigned['character_name']} - {assigned['class_name']} · {role}"
                                            )
                                        else:
                                            ui.html(
                                                '<div class="app-muted">Drop character here</div>'
                                            )
                                slot_cell.on("dragover.prevent", lambda: None)
                                slot_cell.on("drop", lambda _e, s=slot: handle_drop(s))

        search_text.on("update:model-value", lambda _e: render_pool_and_forms.refresh())
        role_filter.on("update:model-value", lambda _e: render_pool_and_forms.refresh())
        role_filter.props("dense outlined").classes("w-32")
        show_assigned.on(
            "update:model-value", lambda _e: render_pool_and_forms.refresh()
        )

        render_pool_and_forms()


def render_scheduled_raid_card(raid, week_id):
    with ui.element("div").classes("app-panel"):
        with ui.element("div").classes("app-panel-head"):
            ui.html(
                f"<h3>{raid['raid_title']} - {raid['raid_difficulty']} · Group {raid['group_number']}</h3>"
            )

        with ui.element("div").classes("app-panel-body"):
            time_text = raid.get("start_time") or "No start time"
            ui.label(f"{raid['day']} - {time_text}")
            ui.label(f"Order {raid['sort_order']}")
            ui.html(f'<div class="app-muted">{raid.get("notes") or "No notes"}</div>')
            render_assignments(raid, week_id)


@ui.refreshable
def render_raids(week_id):
    try:
        page_data = get_week_detail_page_data(int(week_id))
    except ValueError as exc:
        with ui.element("div").classes("app-panel"):
            with ui.element("div").classes("app-panel-body"):
                ui.label(str(exc))
        return

    day_groups = page_data["day_groups"]

    if not day_groups:
        with ui.element("div").classes("app-panel"):
            with ui.element("div").classes("app-panel-body"):
                ui.label("No scheduled raids yet.")
        return

    render_scheduled_raids(day_groups, week_id)


@ui.page("/weeks/{week_id}")
def week_detail_page(week_id: str):
    try:
        page_data = get_week_detail_page_data(int(week_id))
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
                    render_week_sidebar(week_id, raid_definitions)
            with ui.element("div"):
                render_raids(int(week_id))


def create_assignment_from_form(
    week_id,
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
    fresh = get_week_detail_page_data(int(week_id))
    scheduled_raids = fresh["scheduled_raids"]
    all_assignments = fresh["scheduled_raid_assignments"]

    raid_def_by_scheduled = {
        int(r["id"]): int(r["raid_definition_id"]) for r in scheduled_raids
    }

    target_scheduled_id = int(scheduled_raid_id)
    target_raid_def_id = raid_def_by_scheduled.get(target_scheduled_id)

    char_week_assignments = [
        a for a in all_assignments if int(a["character_id"]) == int(character_id)
    ]

    char_raid_defs = {
        raid_def_by_scheduled.get(int(a["scheduled_raid_id"]))
        for a in char_week_assignments
        if raid_def_by_scheduled.get(int(a["scheduled_raid_id"])) is not None
    }

    # Cannot do same raid definition twice in the same week
    if target_raid_def_id in char_raid_defs:
        ui.notify("Character already assigned to this raid this week.", color="warning")
        return

    # Max 3 different raids per week
    if len(char_raid_defs) >= 3:
        ui.notify("Character reached weekly raid limit (3).", color="warning")
        return
    create_assignment_record(
        scheduled_raid_id,
        int(character_id),
        int(slot_order),
        assign_notes.strip() or "",
    )
    on_success_refresh()
    ui.notify("Assignment created", color="positive")


def create_raid_from_form(
    week_id,
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
        week_id,
        int(raid_definition_id.value or 0),
        day.value or "",
        int(group_number.value or 0),
        start_time.value or None,
        notes.value.strip() or "",
        int(sort_order.value or 0),
    )
    render_raids.refresh(week_id)
    ui.notify("Raid created.", color="positive")
