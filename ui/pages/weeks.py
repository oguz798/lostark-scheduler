from nicegui import ui

from app.services.weeks_service import (
    create_week_record,
    delete_week_record,
    force_delete_week_record,
    get_week_scheduled_raid_count,
    get_weeks_page_data,
)
from ui.components.layout import app_shell


@ui.refreshable
def render_weeks(pending_delete_week_id, delete_week_dialog):
    page_data = get_weeks_page_data()
    weeks = page_data["weeks"]
    if not weeks:
        with ui.element("div").classes("app-panel"):
            with ui.element("div").classes("app-panel-body"):
                ui.label("No weeks created yet.")
        return

    for week in weeks:
        with ui.element("div").classes("app-panel"):
            with ui.element("div").classes("app-panel-head"):
                ui.html(f"<h2>Week Beginning {week['start_date']}</h2>")

            with ui.element("div").classes("app-panel-body"):
                ui.html(
                    f'<div class="app-muted">{week.get("notes") or "No notes"}</div>'
                )
                ui.link("Open week", f"/weeks/{week['id']}").classes("app-link-button")
                with ui.row():
                    ui.button(
                        "Delete",
                        on_click=lambda _event, week_id=week["id"]: delete_week_item(
                            week_id,
                            pending_delete_week_id,
                            delete_week_dialog,
                        ),
                    ).classes("app-button-danger")


def create_week(start_date, notes):
    create_week_record(start_date.value or "", notes.value or "")
    render_weeks.refresh()
    ui.notify("Week created.", color="positive")


def delete_week_item(week_id: int, pending_delete_week_id, delete_week_dialog):
    scheduled_raid_count = get_week_scheduled_raid_count(week_id)

    if scheduled_raid_count == 0:
        delete_week_record(week_id)
        render_weeks.refresh()
        ui.notify("Week deleted.", color="positive")
        return

    pending_delete_week_id["value"] = week_id
    delete_week_dialog.open()


def force_delete_week(pending_delete_week_id, delete_week_dialog):
    week_id = pending_delete_week_id["value"]
    if week_id is None:
        return

    force_delete_week_record(week_id)
    pending_delete_week_id["value"] = None
    delete_week_dialog.close()
    render_weeks.refresh()
    ui.notify("Week deleted.", color="positive")


@ui.page("/weeks")
def weeks_page():
    page_data = get_weeks_page_data()
    default_start_date = page_data["default_start_date"]
    pending_delete_week_id = {"value": None}

    with ui.dialog() as delete_week_dialog, ui.card():
        ui.label("This week already has scheduled raids.")
        ui.label("Deleting it will also remove those scheduled raids. Are you sure?")

        with ui.row():
            ui.button("Cancel", on_click=delete_week_dialog.close)
            ui.button(
                "Delete Anyway",
                on_click=lambda: force_delete_week(
                    pending_delete_week_id,
                    delete_week_dialog,
                ),
            ).classes("app-button-danger")

    with app_shell("Weeks", "Weekly planning windows and raid schedules"):
        with ui.element("div").classes("app-split"):
            with ui.element("div"):
                with ui.element("div").classes("app-panel"):
                    with ui.element("div").classes("app-panel-head"):
                        ui.html("<h2>Create Week</h2>")

                    with ui.element("div").classes("app-panel-body app-form"):
                        start_date = ui.input("Start Date", value=default_start_date)
                        notes = ui.textarea("Notes")
                        ui.button(
                            "Create Week",
                            on_click=lambda: create_week(start_date, notes),
                        ).classes("app-button-primary")

                with ui.element("div").classes("app-panel"):
                    with ui.element("div").classes("app-panel-head"):
                        ui.html("<h2>Next Week Weds</h2>")
                    with ui.element("div").classes("app-panel-body"):
                        ui.html(f'<div class="app-accent">{default_start_date}</div>')

            with ui.element("div"):
                render_weeks(pending_delete_week_id, delete_week_dialog)
