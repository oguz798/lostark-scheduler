from nicegui import ui

from app.services.search_service import get_search_page_data, prepare_member_import
from app.services.members_service import save_member_roster
from ui.components.layout import app_shell


def _format_item_level(value):
    if value is None:
        return "-"

    return f"{value:.2f}"


# UI action handler: validates member selection, fetches selected roster snapshot, and persists imported characters.
async def import_member_roster(member_id, region: str, name: str, roster_id: int):
    if not member_id.value:
        ui.notify("Select a member first.", color="negative")
        return

    try:
        selected_roster = await prepare_member_import(region, name, roster_id)
    except ValueError as exc:
        ui.notify(str(exc), color="negative")
        return

    save_member_roster(int(member_id.value), selected_roster)
    ui.notify("Roster imported.", color="positive")
    ui.navigate.to("/members")


# Page expects query params (region, name) and renders search candidates for import.
@ui.page("/search")
async def search_page(region: str, name: str):
    try:
        page_data = await get_search_page_data(region, name)
    except ValueError as exc:
        with app_shell("Search", "Find roster results to import"):
            with ui.element("div").classes("app-panel"):
                with ui.element("div").classes("app-panel-body"):
                    ui.label(str(exc))
        return

    results = page_data["results"]
    members = page_data["members"]
    region = page_data["region"]
    name = page_data["name"]

    with app_shell("Search", "Find roster results to import"):
        if not results:
            with ui.element("div").classes("app-panel"):
                with ui.element("div").classes("app-panel-body"):
                    ui.label("No result.")
            return

        for result in results:
            with ui.element("div").classes("app-panel"):
                with ui.element("div").classes("app-panel-head"):
                    ui.html(f"<h2>{result.matched_character_name} · {result.matched_character_class}</h2>")
                    ui.html(
                        f"<div class='app-muted'>Characters: {result.total_characters}</div>"
                    )

                with ui.element("div").classes("app-panel-body app-form"):
                    with ui.element("div").classes("app-panel"):
                        with ui.element("div").classes("app-panel-head"):
                            ui.html("<h3>Top Characters</h3>")
                            ui.html(
                                "<div class='app-muted'>Import saves the top 6 characters shown below. </div>"
                            )
                        with ui.element("div").classes("app-panel-body"):
                            for character in result.top_characters:
                                ui.html(
                                    f"<div class='app-muted'>{character.name} · {character.class_name} · {_format_item_level(character.item_level)}</div>"
                                )

                    member_id = ui.select(
                        {
                            str(member["id"]): member["display_name"]
                            for member in members
                        },
                        label="Import Into Member",
                    )

                    # Capture current result values in default args to avoid late-binding issues inside loop callbacks.
                    async def handle_import(
                        member_id=member_id, roster_id=result.roster_id
                    ):
                        await import_member_roster(member_id, region, name, roster_id)

                    import_button = ui.button(
                        "Import Roster",
                        on_click=handle_import,
                    ).classes("app-button-primary")
                    import_button.disable()

                    def on_member_change(e):
                        if e.value:
                            import_button.enable()
                        else:
                            import_button.disable()

                    member_id.on_value_change(on_member_change)
