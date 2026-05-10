from nicegui import ui
from app.domain.days import PLANNER_DAYS
from app.schemas.week_plan import WeekPlanContext
from ui.pages.week_plan.actions import (
    cancel_availability_edit,
    save_availability_edit,
    start_availability_edit,
)
from ui.pages.week_plan.data import format_availability_cell


def render_top_cards(
    context: WeekPlanContext,
    ui_state: dict,
    refresh_week,
) -> None:
    with ui.element("div").classes("app-top"):
        render_character_pool_card(context)
        render_availability_card(context, ui_state, refresh_week)
        render_schedule_card(context)


def render_character_pool_card(context: WeekPlanContext) -> None:
    with ui.element("div").classes("app-panel app-plan-panel"):
        with ui.element("div").classes("app-panel-head"):
            ui.html("<h2>Character Pool</h2>")
        with ui.element("div").classes("app-panel-body"):
            with ui.element("div").style(
                "display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:8px;"
            ):
                for member_data in context.character_pool.values():
                    characters = member_data.characters
                    with ui.expansion(
                        f"{member_data.member_name} ({len(characters)})",
                        value=False,
                    ).classes("w-full"):
                        with ui.row().classes("gap-2"):
                            for character in characters:
                                ui.html(f"<span class='chip'>{character.name}</span>")


def render_availability_card(
    context: WeekPlanContext,
    ui_state: dict,
    refresh_week,
) -> None:
    with ui.element("div").classes("app-panel app-plan-panel"):
        with ui.element("div").classes("app-panel-head"):
            ui.html("<h2>Availability</h2>")
        with ui.element("div").classes("app-panel-body app-availability-scroll"):
            with ui.element("div").classes("app-availability-grid"):
                for heading in ["Member", *PLANNER_DAYS]:
                    ui.html(
                        f"<div class='app-availability-cell app-availability-head'>{heading}</div>"
                    )

                for member_availability in context.member_availability_rows:
                    ui.html(
                        f"<div class='app-availability-cell'>{member_availability['member_name']}</div>"
                    )

                    for day in PLANNER_DAYS:
                        day_availability = member_availability["days"][day]
                        availability_data = {
                            "member_id": member_availability["member_id"],
                            "day": day,
                            "status": day_availability["status"],
                            "available_after": day_availability["available_after"],
                            "notes": day_availability["notes"],
                        }
                        if _is_editing_availability_cell(availability_data, ui_state):
                            render_availability_cell_editor(
                                availability_data,
                                ui_state,
                                refresh_week,
                            )
                        else:
                            render_availability_read_cell(
                                availability_data,
                                day_availability,
                                ui_state,
                                refresh_week,
                            )


def render_availability_read_cell(
    availability_data: dict,
    day_availability: dict,
    ui_state: dict,
    refresh_week,
) -> None:
    with ui.element("div").classes("app-availability-cell"):
        ui.button(
            format_availability_cell(day_availability),
            on_click=lambda: start_availability_edit(
                availability_data,
                ui_state,
                refresh_week,
            ),
        ).props("flat dense no-caps").classes("app-availability-read-button")


def render_availability_cell_editor(
    availability_data: dict,
    ui_state: dict,
    refresh_week,
) -> None:

    draft = ui_state["availability_draft"]

    with ui.element("div").classes("app-availability-cell"):
        with ui.element("div").classes("app-availability-editor"):
            ui.select(
                ["available", "unavailable", "after"], value=draft["status"]
            ).props("dense outlined").classes(
                "app-availability-status"
            ).on_value_change(
                lambda e, d=draft: (
                    d.__setitem__("status", e.value or "available"),
                    d.__setitem__(
                        "available_after",
                        "18:00"
                        if (e.value == "after" and not d.get("available_after"))
                        else "",
                    ),
                    refresh_week(ui_state),
                )
            )

            if draft.get("status") == "after":
                ui.input(
                    "Time",
                    value=draft.get("available_after") or "18:00",
                    placeholder="18:00",
                ).props("dense outlined mask='##:##'").classes(
                    "app-availability-time"
                ).on_value_change(
                    lambda e, d=draft: d.__setitem__(
                        "available_after",
                        e.value or "",
                    )
                )

            with ui.row().classes("items-center gap-1"):
                can_save = _is_availability_draft_saveable(draft)

                ui.button(
                    icon="check",
                    on_click=lambda: save_availability_edit(
                        availability_data, ui_state, refresh_week
                    ),
                ).props("" if can_save else "disable").classes("app-icon-btn")

                ui.button(
                    icon="close",
                    on_click=lambda: cancel_availability_edit(
                        availability_data,
                        ui_state,
                        refresh_week,
                    ),
                ).classes("app-icon-btn app-icon-btn-danger")


def _is_availability_draft_saveable(draft: dict) -> bool:
    if draft.get("status") != "after":
        return True

    return bool(draft.get("available_after"))


def _is_editing_availability_cell(
    availability_data: dict,
    ui_state: dict,
) -> bool:

    editing = ui_state["editing_availability"]
    if not editing:
        return False

    return (
        editing["member_id"] == availability_data["member_id"]
        and editing["day"] == availability_data["day"]
    )


def render_schedule_card(context: WeekPlanContext) -> None:
    with ui.element("div").classes("app-panel app-plan-panel"):
        with ui.element("div").classes("app-panel-head"):
            ui.html("<h2>Schedule</h2>")
        with ui.element("div").classes("app-panel-body app-availability-scroll"):
            with ui.element("div").classes("app-schedule-grid"):
                for heading in ["Day", "Time", "Raid", "Notes"]:
                    ui.html(
                        f"<div class='app-schedule-cell app-schedule-head'>{heading}</div>"
                    )

                for row in context.schedule_rows:
                    for cell in [row.day, row.time_text, row.raid_text, row.notes]:
                        ui.html(f"<div class='app-schedule-cell'>{cell}</div>")
