from nicegui import ui

from app.schemas.week_plan import (
    PlanAssignment,
    PlanGroup,
)
from ui.pages.week_plan.actions import (
    cancel_group_schedule_edit,
    delete_assignment_action,
    delete_raid_group_action,
    handle_character_drop,
    start_group_schedule_edit,
    start_slot_assignment_drag,
    update_group_schedule_action,
)
from ui.pages.week_plan.data import build_group_schedule_draft
from ui.pages.render_formatting import format_combat_power, format_item_level


def format_group_schedule_label(group_name: str, group_data: PlanGroup) -> str:
    day = group_data.day
    start_time = group_data.start_time

    if not day:
        return f"{group_name} · unscheduled"

    time_text = start_time or "after"
    return f"{group_name} · {day} · {time_text}"


def render_group_grid(
    raid_name: str,
    groups: dict[str, PlanGroup],
    ui_state: dict,
    refresh_week,
) -> None:
    with (
        ui.element("div")
        .classes("app-group-grid")
        .style(f"grid-template-columns: repeat({len(groups)}, max-content);")
    ):
        for group_name, group_data in sorted(
            groups.items(),
            key=lambda item: item[1].group_number,
        ):
            render_group_card(raid_name, group_name, group_data, ui_state, refresh_week)


def render_group_card(
    raid_name: str,
    group_name: str,
    group_data: PlanGroup,
    ui_state: dict,
    refresh_week,
) -> None:
    group_label = format_group_schedule_label(group_name, group_data)
    group_key = f"{raid_name}::{group_name}"
    is_schedule_editing = (
        ui_state["editing_group_schedule_id"] == group_data.raid_group_id
    )
    group_classes = "app-panel app-group-shell"
    if len(group_data.parties) == 1:
        group_classes += " app-group-shell-single"
    else:
        group_classes += " app-group-shell-double"

    with ui.element("div").classes(group_classes):
        render_group_header(group_label, group_data, ui_state, refresh_week)

        with ui.element("div").classes("app-group-content"):
            render_party_grid(group_data, ui_state, refresh_week)
            render_group_footer(
                group_key,
                group_data,
                ui_state,
                refresh_week,
                is_schedule_editing,
            )


def render_group_header(
    group_label: str,
    group_data: PlanGroup,
    ui_state: dict,
    refresh_week,
) -> None:
    with ui.element("div").classes("app-group-head"):
        ui.html(f"<span>{group_label}</span>")
        with ui.row().classes("items-center gap-1"):
            ui.button(
                icon="edit",
                on_click=lambda _e, gd=group_data: start_group_schedule_edit(
                    gd,
                    ui_state,
                    refresh_week,
                ),
            ).classes("app-icon-btn")
            ui.button(
                icon="delete",
                on_click=lambda _e, gd=group_data: delete_raid_group_action(
                    gd,
                    ui_state,
                    refresh_week,
                ),
            ).classes("app-icon-btn app-icon-btn-danger")


def render_party_grid(
    group_data: PlanGroup,
    ui_state: dict,
    refresh_week,
) -> None:
    parties = group_data.parties

    with (
        ui.element("div")
        .classes("app-party-grid")
        .style(f"grid-template-columns: repeat({len(parties)}, minmax(0, 1fr));")
    ):
        for party_name, slots in parties.items():
            render_party_column(party_name, slots, group_data, ui_state, refresh_week)


def render_party_column(
    party_name: str,
    slots: list[PlanAssignment | None],
    group_data: PlanGroup,
    ui_state: dict,
    refresh_week,
) -> None:
    party_label = "Party 1" if party_name == "P1" else "Party 2"

    with ui.element("div").classes("app-party-col"):
        ui.html(f"<div class='app-party-head'>{party_label}</div>")

        for row_idx, assignment in enumerate(slots):
            slot_order = row_idx + 1 if party_name == "P1" else row_idx + 5
            render_assignment_slot(
                assignment,
                slot_order,
                group_data,
                ui_state,
                refresh_week,
                delete_assignment_action,
                start_slot_assignment_drag,
                handle_character_drop,
            )


def render_assignment_slot(
    assignment: PlanAssignment | None,
    slot_order: int,
    group_data: PlanGroup,
    ui_state: dict,
    refresh_week,
    on_assignment_delete,
    on_assignment_drag_start,
    on_character_drop,
) -> None:
    # Support-only slots are fixed by index for both 4- and 8-player groups.
    required_role = "SUP" if slot_order in (4, 8) else "DPS"
    slot_role_class = (
        "app-slot-required-sup" if required_role == "SUP" else "app-slot-required-dps"
    )

    with ui.element("div").classes(f"app-slot {slot_role_class}") as slot_cell:
        if required_role == "SUP":
            ui.html(f"<div class='app-slot-required-label'>{required_role}</div>")

        if assignment:
            render_slot_assignment(
                assignment,
                ui_state,
                refresh_week,
                on_assignment_delete,
                on_assignment_drag_start,
            )
        else:
            ui.html("<span class='app-muted'>Empty</span>")

    slot_cell.on("dragover.prevent", lambda: None)
    slot_cell.on(
        "drop",
        lambda _e, gd=group_data, so=slot_order: on_character_drop(
            gd,
            so,
            ui_state,
            refresh_week,
        ),
    )


def render_slot_assignment(
    assignment: PlanAssignment,
    ui_state: dict,
    refresh_week,
    on_assignment_delete,
    on_assignment_drag_start,
) -> None:
    with (
        ui.element("div")
        .classes("app-slot-assignment")
        .props("draggable=true") as assigned_drag
    ):
        ui.html(
            f"<div class='app-slot-text'>"
            f"<div class='app-slot-class'>{assignment.class_name}</div>"
            f"<div class='app-slot-member'>{assignment.member_name}</div>"
            f"</div>"
        )
        with ui.tooltip().classes("app-slot-tooltip"):
            ui.html(_build_slot_hover_html(assignment))

        ui.button(
            icon="delete",
            on_click=lambda _e, a=assignment: on_assignment_delete(
                a,
                ui_state,
                refresh_week,
            ),
        ).classes("app-icon-btn app-icon-btn-danger")

    assigned_drag.on(
        "dragstart",
        lambda _e, a=assignment: on_assignment_drag_start(a, ui_state),
    )


def render_group_footer(
    group_key: str,
    group_data: PlanGroup,
    ui_state: dict,
    refresh_week,
    is_schedule_editing: bool,
) -> None:
    with ui.element("div").classes("app-group-footer"):
        render_free_spots(group_data.parties)
        render_group_note(group_key, ui_state)

        if is_schedule_editing:
            render_group_schedule_editor(group_data, ui_state, refresh_week)


def render_free_spots(parties) -> None:
    group_summary = []

    for party_name, slots in parties.items():
        party_label = "Party 1" if party_name == "P1" else "Party 2"
        empty_count = sum(1 for slot in slots if not slot)
        group_summary.append(f"{party_label}: {empty_count} open")

    ui.html(
        "<div class='app-free-row'><strong>Free spots:</strong> "
        + ", ".join(group_summary)
        + "</div>"
    )


def render_group_note(group_key: str, ui_state: dict) -> None:
    ui.input(
        "Group Note",
        value=ui_state["group_notes"].get(group_key, ""),
    ).classes("w-full app-group-note").props("dense outlined").on(
        "update:model-value",
        lambda e, k=group_key: ui_state["group_notes"].__setitem__(k, e.args or ""),
    )


def render_group_schedule_editor(
    group_data: PlanGroup,
    ui_state: dict,
    refresh_week,
) -> None:
    schedule_key = group_data.raid_group_id
    schedule_draft = ui_state["group_schedule_drafts"].setdefault(
        schedule_key,
        build_group_schedule_draft(group_data),
    )

    with ui.row().classes("items-center gap-2 app-group-schedule"):
        ui.select(
            ["Wed", "Thu", "Fri", "Sat", "Sun"],
            value=schedule_draft["day"],
            label="Day",
        ).props("dense outlined").on_value_change(
            lambda e, d=schedule_draft: d.__setitem__("day", e.value or "Wed"),
        )
        ui.input(
            "Time",
            value=schedule_draft["start_time"],
            placeholder="18:00",
        ).props("dense outlined mask='##:##'").on_value_change(
            lambda e, d=schedule_draft: d.__setitem__("start_time", e.value or ""),
        )
        ui.number(
            "Order",
            value=schedule_draft["sort_order"],
        ).props("dense outlined").on_value_change(
            lambda e, d=schedule_draft: d.__setitem__("sort_order", e.value or 0),
        )
        ui.button(
            icon="check",
            on_click=lambda _e, gd=group_data, d=schedule_draft: (
                update_group_schedule_action(gd, ui_state, d, refresh_week)
            ),
        ).classes("app-icon-btn")
        ui.button(
            icon="close",
            on_click=lambda _e, gd=group_data: cancel_group_schedule_edit(
                gd,
                ui_state,
                refresh_week,
            ),
        ).classes("app-icon-btn app-icon-btn-danger")


def _build_slot_hover_html(assignment) -> str:
    ilvl = format_item_level(assignment.item_level)
    cp = format_combat_power(assignment.combat_power_score)
    role = (assignment.combat_role or "-").upper()
    char_name = assignment.character_name or "-"

    return (
        f"<div><strong>Character:</strong> {char_name}</div>"
        f"<div><strong>iLvl:</strong> {ilvl}</div>"
        f"<div><strong>CP:</strong> {cp}</div>"
        f"<div><strong>Role:</strong> {role}</div>"
    )
