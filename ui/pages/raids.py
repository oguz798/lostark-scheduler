from nicegui import ui

from app.services.raids_service import (
    create_raid_definition_record,
    delete_raid_definition_record,
    force_delete_raid_definition_record,
    get_raid_definition_usage_count,
    list_raid_definitions,
)
from ui.components.layout import app_shell


@ui.refreshable
def render_raid_definitions(pending_delete_raid_definition_id, delete_raid_definition_dialog):
    raids = list_raid_definitions()
    with ui.element("div").classes("app-content"):
        with ui.element("div").classes("app-panel mb-5"):
            with ui.element("div").classes("app-panel-head"):
                ui.html("<h2>Raids</h2>")
            with ui.element("div").classes("app-panel-body"):
                ui.html(
                    '<div class="app-muted">Available raid definitions for planning.</div>'
                )
        if not raids:
            with ui.element("div").classes("app-panel"):
                with ui.element("div").classes("app-panel-body"):
                    ui.label("No raid definitions created yet.")
            return
        for raid in raids:
            with ui.element("div").classes("raid-row"):
                with ui.element("div").classes("raid-row-grid"):
                    with ui.element("div").classes("raid-row-main"):
                        ui.html(f"<h2>{raid['title']} - {raid['difficulty']}</h2>")

                        with ui.element("div").classes("raid-row-meta"):
                            ui.label(f"Player Count: {raid['player_count']}")
                            ui.label(f"Min Item Level: {raid['min_item_level']}")

                        ui.html(
                            f'<div class="app-muted">{raid.get("notes") or "No notes"}</div>'
                        )
                    with ui.element("div").classes("raid-row-actions"):
                        ui.button(
                            "Delete",
                            on_click=lambda _event, raid_id=raid["id"]: delete_raid_definition_item(
                                raid_id,
                                pending_delete_raid_definition_id,
                                delete_raid_definition_dialog,
                            ),
                        ).classes("app-button-danger")


def create_raid_definition_from_form(title, difficulty, player_count, min_item_level, notes):
    create_raid_definition_record(
        title.value or "",
        difficulty.value or "",
        int(player_count.value or 0),
        float(min_item_level.value or 0),
        notes.value or "",
    )
    render_raid_definitions.refresh()
    ui.notify("Raid definition created.", color="positive")


def delete_raid_definition_item(
    raid_definition_id: int,
    pending_delete_raid_definition_id,
    delete_raid_definition_dialog,
):
    usage_count = get_raid_definition_usage_count(raid_definition_id)

    if usage_count == 0:
        delete_raid_definition_record(raid_definition_id)
        render_raid_definitions.refresh()
        ui.notify("Raid definition deleted.", color="positive")
        return

    pending_delete_raid_definition_id["value"] = raid_definition_id
    delete_raid_definition_dialog.open()


def force_delete_raid_definition(
    pending_delete_raid_definition_id,
    delete_raid_definition_dialog,
):
    raid_definition_id = pending_delete_raid_definition_id["value"]
    if raid_definition_id is None:
        return

    force_delete_raid_definition_record(raid_definition_id)
    pending_delete_raid_definition_id["value"] = None
    delete_raid_definition_dialog.close()
    render_raid_definitions.refresh()
    ui.notify("Raid definition deleted.", color="positive")


@ui.page("/raids")
def raids_page():
    pending_delete_raid_definition_id = {"value": None}

    with ui.dialog() as delete_raid_definition_dialog, ui.card():
        ui.label("This raid definition is already used by scheduled raids.")
        ui.label("Deleting it will also remove those scheduled raids. Are you sure?")

        with ui.row():
            ui.button("Cancel", on_click=delete_raid_definition_dialog.close)
            ui.button(
                "Delete Anyway",
                on_click=lambda: force_delete_raid_definition(
                    pending_delete_raid_definition_id,
                    delete_raid_definition_dialog,
                ),
            ).classes("app-button-danger")

    with app_shell("Raids", "Available raid definitions for weekly planning"):
        with ui.element("div").classes("app-split"):
            with ui.element("div"):
                with ui.element("div").classes("app-panel"):
                    with ui.element("div").classes("app-panel-head"):
                        ui.html("<h2>Create Raid</h2>")
                    with ui.element("div").classes("app-panel-body app-form"):
                        with ui.row().classes("w-full gap-4"):
                            title = ui.input("Title").classes("flex-1")
                            difficulty = ui.input("Difficulty").classes("flex-1")
                        with ui.row().classes("w-full gap-4"):
                            player_count = ui.number("Player Count", value=8).classes(
                                "flex-1"
                            )
                            min_item_level = ui.number(
                                "Min Item Level", value=0
                            ).classes("flex-1")

                        notes = ui.textarea("Notes")
                        ui.button(
                            "Create Raid",
                            on_click=lambda: create_raid_definition_from_form(
                                title, difficulty, player_count, min_item_level, notes
                            ),
                        ).classes("app-button-primary")

            with ui.element("div"):
                render_raid_definitions(
                    pending_delete_raid_definition_id,
                    delete_raid_definition_dialog,
                )
