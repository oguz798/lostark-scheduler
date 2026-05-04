from nicegui import ui

from ui.components.layout import app_shell
from ui.pages import members, raids, weeks, week_detail, search


@ui.page("/")
def index():

    with app_shell("Home Page", "Weekly planning tool"):
        with ui.element("div").classes("app-panel"):
            with ui.element("div").classes("app-panel-head"):
                ui.html("<h2>Search</h2>")

            with ui.element("div").classes("app-panel-body app-form"):
                region = ui.select(
                    {"ce": "CE", "na": "NA"},
                    label="Region",
                    value="ce",
                ).props("outlined")
                name = ui.input("Name")
                ui.button(
                    "Search",
                    on_click=lambda: ui.navigate.to(
                        f"/search?region={region.value}&name={name.value}"
                    ),
                ).classes("app-button-primary")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Lost Ark Scheduler")
