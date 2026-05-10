from nicegui import ui

from app.services.raids_service import (
    create_raid_record,
    delete_raid_record,
    force_delete_raid_record,
    get_raid_usage_count,
    list_raids,
)
from ui.components.layout import app_shell


@ui.refreshable
def render_raids(pending_delete_raid_id, delete_raid_dialog):
    raids = list_raids()
    with ui.element("div").classes("app-content"):
        with ui.element("div").classes("app-panel mb-5"):
            with ui.element("div").classes("app-panel-head"):
                ui.html("<h2>Raids</h2>")
            with ui.element("div").classes("app-panel-body"):
                ui.html(
                    '<div class="app-muted">Available raids for planning.</div>'
                )
        if not raids:
            with ui.element("div").classes("app-panel"):
                with ui.element("div").classes("app-panel-body"):
                    ui.label("No raids created yet.")
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
                            on_click=lambda _event, raid_id=raid["id"]: delete_raid_item(
                                raid_id,
                                pending_delete_raid_id,
                                delete_raid_dialog,
                            ),
                        ).classes("app-button-danger")


def create_raid_from_form(title, difficulty, player_count, min_item_level, notes):
    create_raid_record(
        title.value or "",
        difficulty.value or "",
        int(player_count.value or 0),
        float(min_item_level.value or 0),
        notes.value or "",
    )
    render_raids.refresh()
    ui.notify("Raid created.", color="positive")


def delete_raid_item(
    raid_id: int,
    pending_delete_raid_id,
    delete_raid_dialog,
):
    usage_count = get_raid_usage_count(raid_id)

    if usage_count == 0:
        delete_raid_record(raid_id)
        render_raids.refresh()
        ui.notify("Raid deleted.", color="positive")
        return

    pending_delete_raid_id["value"] = raid_id
    delete_raid_dialog.open()


def force_delete_raid(
    pending_delete_raid_id,
    delete_raid_dialog,
):
    raid_id = pending_delete_raid_id["value"]
    if raid_id is None:
        return

    force_delete_raid_record(raid_id)
    pending_delete_raid_id["value"] = None
    delete_raid_dialog.close()
    render_raids.refresh()
    ui.notify("Raid deleted.", color="positive")


@ui.page("/raids")
def raids_page():
    pending_delete_raid_id = {"value": None}

    with ui.dialog() as delete_raid_dialog, ui.card():
        ui.label("This raid is already used by raid groups.")
        ui.label("Deleting it will also remove those raid groups. Are you sure?")

        with ui.row():
            ui.button("Cancel", on_click=delete_raid_dialog.close)
            ui.button(
                "Delete Anyway",
                on_click=lambda: force_delete_raid(
                    pending_delete_raid_id,
                    delete_raid_dialog,
                ),
            ).classes("app-button-danger")

    with app_shell("Raids", "Available raids for weekly planning"):
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
                            on_click=lambda: create_raid_from_form(
                                title, difficulty, player_count, min_item_level, notes
                            ),
                        ).classes("app-button-primary")

            with ui.element("div"):
                render_raids(
                    pending_delete_raid_id,
                    delete_raid_dialog,
                )
