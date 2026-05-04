from contextlib import contextmanager
from pathlib import Path

from nicegui import ui

APP_CSS = Path("ui/styles/app.css").read_text(encoding="utf-8")


@contextmanager
def app_shell(title: str, subtitle: str | None = None):
    ui.html(f"<style>{APP_CSS}</style>")

    with ui.element("div").classes("app-page"):
        with ui.element("div").classes("app-topbar"):
            with ui.element("div").classes("app-title-wrap"):
                ui.html(f"<h1>{title}</h1>")
                if subtitle:
                    ui.html(f"<p>{subtitle}</p>")

            with ui.element("div").classes("app-actions"):
                ui.link("Home", "/").classes("app-link-button")
                ui.link("Members", "/members").classes("app-link-button")
                ui.link("Raids", "/raids").classes("app-link-button")
                ui.link("Weeks", "/weeks").classes("app-link-button")

        with ui.element("div").classes("app-content"):
            yield
