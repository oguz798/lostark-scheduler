from pathlib import Path

from nicegui import ui

from app.services.weeks_service import get_week_detail_page_data
from app.services.availability_service import fetch_week_member_availability
from ui.components.layout import app_shell
from ui.pages.week_plan.data import (
    build_week_plan_context,
)
from ui.pages.week_plan.render_top import render_top_cards
from ui.pages.week_plan.render_raids import render_raid_cards


def _load_css() -> str:
    return Path("ui/styles/week_plan.css").read_text(encoding="utf-8")


@ui.refreshable
def render_week(ui_state: dict) -> None:
    page_data = get_week_detail_page_data(ui_state["week_id"])
    member_availability_rows = fetch_week_member_availability(ui_state["week_id"])

    context = build_week_plan_context(page_data, member_availability_rows)

    with ui.element("div").classes("app-week-plan-page"):
        with ui.element("div").classes("app-week-plan-layout"):
            with ui.element("div").classes("app-week-plan-main"):
                render_top_cards(
                    context,
                    ui_state,
                    render_week.refresh,
                )
                render_raid_cards(
                    context,
                    ui_state,
                    render_week.refresh,
                )


@ui.page("/weeks/{week_id}/plan")
def week_page(week_id: str) -> None:
    ui_state = {
        "week_id": int(week_id),
        "raid_notes": {},
        "group_notes": {},
        "expanded_raids": set(),
        "expanded_eligible_members": set(),
        "group_schedule_drafts": {},
        "editing_group_schedule_id": None,
        "open_assignment_raid_name": None,
        "drag": {
            "character_id": None,
            "combat_role": "",
            "source_assignment_id": None,
            "source_raid_group_id": None,
            "source_slot_order": None,
        },
        "assignment_filters": {
            "search_query": "",
            "role_filter": "ALL",
            "show_assigned": False,
        },
        "editing_availability": None,
        "availability_draft": {},
    }

    try:
        page_data = get_week_detail_page_data(ui_state["week_id"])
    except ValueError as exc:
        with app_shell("Week Detail"):
            with ui.element("div").classes("app-panel"):
                with ui.element("div").classes("app-panel-body"):
                    ui.label(str(exc))
        return

    week = page_data["week"]

    with app_shell(
        f"Week Beginning {week['start_date']}",
        week.get("notes") or "Build and review the weekly raid schedule.",
    ):
        ui.html(f"<style>{_load_css()}</style>")
        render_week(ui_state)
