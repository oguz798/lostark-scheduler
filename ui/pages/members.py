from nicegui import ui

from app.services.members_service import (
    refresh_member_record,
    get_members_page_data,
    create_member_record,
    create_character_record,
    force_delete_member_record,
    force_delete_character_record,
    update_member_character,
    refresh_character_record,
    update_member_roster_main,
    update_member_fields,
)
from ui.components.layout import app_shell


async def refresh_member(member_id: int, ui_state):

    try:
        await refresh_member_record(member_id)
    except ValueError as exc:
        ui.notify(str(exc), color="negative")
        return
    render_members.refresh(ui_state)
    ui.notify("Member refreshed.", color="positive")


def save_roster_main(member_id: int, selected_name, ui_state):
    try:
        update_member_roster_main(member_id, selected_name or "")
    except ValueError as exc:
        ui.notify(str(exc), color="negative")
        return

    ui_state["main_picker_member_id"] = None
    render_members.refresh(ui_state)
    ui.notify("Roster main character updated.", color="positive")


def start_character_edit(character: dict, ui_state: dict) -> None:

    ui_state["edit"]["character_id"] = character["id"]
    ui_state["edit"]["member_id"] = character["member_id"]
    ui_state["edit"]["role"] = character["combat_role"]
    ui_state["edit"]["power"] = character["combat_power_score"]
    render_members.refresh(ui_state)


def save_character_edit(ui_state: dict) -> None:
    update_member_character(
        ui_state["edit"]["character_id"],
        ui_state["edit"]["member_id"],
        ui_state["edit"]["role"],
        ui_state["edit"]["power"],
    )
    ui_state["edit"]["character_id"] = None
    render_members.refresh(ui_state)
    ui.notify("Edit success", color="positive")


def cancel_character_edit(ui_state: dict):
    ui_state["edit"]["character_id"] = None
    render_members.refresh(ui_state)
    ui.notify("Edit cancelled")


async def add_character(member_id, character_name_input, ui_state):
    await create_character_record(member_id, character_name_input.value)
    character_name_input.value = ""
    render_members.refresh(ui_state)
    ui.notify("Character added.", color="positive")


async def refresh_character(member_id, character_id, ui_state):
    try:
        await refresh_character_record(member_id, character_id)
        ui.notify("Character refreshed from api", color="positive")
        render_members.refresh(ui_state)
    except ValueError as exc:
        ui.notify(str(exc), color="negative")


def render_member_header(member: dict, characters_by_member, ui_state):

    is_pending_member_delete = ui_state["delete_member_id"] == member["id"]

    with ui.element("div").classes("member-head-grid"):
        with ui.element("div").classes("member-head-main"):
            ui.html(f"<h2>{member['display_name']}</h2>")
            ui.html(
                f"<div class='app-muted'>{member.get('discord_name') or 'No Discord name set'}</div>"
            )

        with ui.element("div").classes("member-head-actions"):
            with ui.row().classes("items-center gap-2"):
                region = member.get("region") or "-"
                world = member.get("world") or "-"
                roster_name = member.get("roster_name") or "-"
                ui.html(f"<span class='chip'>{region}</span>")
                ui.html(f"<span class='chip'>{world}</span>")

                def open_main_picker(member_id: int, ui_state: dict):
                    ui_state["main_picker_member_id"] = member_id
                    render_members.refresh(ui_state)

                if ui_state["main_picker_member_id"] == member["id"]:
                    member_chars = characters_by_member.get(member["id"], [])
                    options = [c["name"] for c in member_chars]

                    roster_select = ui.select(options, value=roster_name).classes(
                        "gold chip"
                    )

                    roster_select.on_value_change(
                        lambda e, mid=member["id"]: save_roster_main(
                            mid, e.value, ui_state
                        )
                    )
                else:
                    chip = ui.html(
                        f"<span class='gold chip cursor-pointer'>{roster_name}</span>"
                    )
                    chip.on(
                        "click",
                        lambda _e, mid=member["id"]: open_main_picker(mid, ui_state),
                    )

                async def handle_refresh_click(_e, m=member["id"]):
                    await refresh_member(m, ui_state)

                ui.button(
                    icon="refresh",
                    on_click=handle_refresh_click,
                ).classes("app-icon-btn")
                ui.button(
                    icon="edit",
                    on_click=lambda _e, m=member: start_member_edit(m, ui_state),
                ).classes("app-icon-btn")

                if not is_pending_member_delete:
                    ui.button(
                        icon="delete",
                        on_click=lambda _e, member_id=member["id"]: start_member_delete(
                            member_id, ui_state
                        ),
                    ).classes("app-button-danger")
                else:
                    ui.button(
                        icon="check",
                        on_click=lambda _e, member_id=member["id"]: delete_member(
                            member_id, ui_state
                        ),
                    ).classes("app-button-danger")
                    ui.button(
                        icon="close", on_click=lambda _e: cancel_member_delete(ui_state)
                    ).classes("app-link-button")


def render_member_meta(member: dict, latest_sync: str, ui_state: dict):
    is_editing_member = ui_state["member_edit"]["member_id"] == member["id"]
    created_at = member.get("created_at_formatted") or "Not tracked"

    with ui.element("div").classes("app-panel-body"):
        if not is_editing_member:
            notes = (member.get("notes") or "").strip() or "No notes added yet."
            ui.html(f"<div>{notes}</div>")
            ui.html(f"<div class='app-muted'>Created: {created_at}</div>")
            ui.html(f"<div class='app-muted'>Last refresh: {latest_sync}</div>")
        else:
            name_input = ui.input("Name", value=ui_state["member_edit"]["display_name"])
            name_input.on_value_change(
                lambda e: ui_state["member_edit"].__setitem__("display_name", e.value)
            )

            discord_input = ui.input(
                "Discord Name",
                value=ui_state["member_edit"]["discord_name"],
            )
            discord_input.on_value_change(
                lambda e: ui_state["member_edit"].__setitem__("discord_name", e.value)
            )

            notes_input = ui.textarea("Notes", value=ui_state["member_edit"]["notes"])
            notes_input.on_value_change(
                lambda e: ui_state["member_edit"].__setitem__("notes", e.value)
            )

            with ui.row().classes("items-center gap-2"):
                ui.button(
                    icon="check",
                    on_click=lambda _e: save_member_edit(ui_state),
                ).classes("app-icon-btn")
                ui.button(
                    icon="close",
                    on_click=lambda _e: cancel_member_edit(ui_state),
                ).classes("app-icon-btn app-icon-btn-danger")


def render_characters_section(member_id, member_main_name, ui_state):

    with ui.element("div").classes("app-panel"):
        with ui.element("div").classes("app-panel-body"):
            is_open = member_id in ui_state["expanded_members"]

            expansion = ui.expansion("Show characters", value=is_open).classes(
                "w-full block"
            )

            def on_expand_change(e, mid=member_id):
                opened = bool(e.value)
                if opened:
                    ui_state["expanded_members"].add(mid)
                else:
                    ui_state["expanded_members"].discard(mid)

            expansion.on_value_change(on_expand_change)

            with expansion:
                render_member_characters(member_id, member_main_name, ui_state)


def render_member_characters(member_id, member_main_name, ui_state):

    try:
        page_data = get_members_page_data()
    except ValueError as exc:
        with app_shell("Members"):
            with ui.element("div").classes("app-panel"):
                with ui.element("div").classes("app-panel-body"):
                    ui.label(str(exc))
        return

    characters = page_data["characters_by_member"].get(member_id, [])
    if not characters:
        ui.label("No characters imported yet.").classes("app-muted")
        return

    for character in characters:
        is_main = (
            character["name"].strip().lower()
            == (member_main_name or "").strip().lower()
        )
        item_level = character.get("item_level")
        item_level_text = (
            "-" if item_level is None else f"{item_level:.2f}".rstrip("0").rstrip(".")
        )
        combat_power = character.get("combat_power_score")
        combat_power_text = (
            "-"
            if combat_power is None
            else f"{combat_power:.2f}".rstrip("0").rstrip(".")
        )
        role_text = character.get("combat_role") or "unknown"

        is_editing = ui_state["edit"]["character_id"] == character["id"]
        is_pending_character_delete = (
            ui_state["delete_character"]["character_id"] == character["id"]
        )
        with ui.element("div").classes("app-panel character-card w-full"):
            with ui.element("div").classes("app-panel-body character-card-body"):
                with (
                    ui.element("div")
                    .classes("character-row-grid")
                    .style(
                        "display:grid; grid-template-columns:minmax(220px,1.7fr) 130px 150px 100px; gap:8px; align-items:center;"
                    )
                ):
                    with ui.element("div").classes("character-col-main"):
                        name_color = "#f2c86b" if is_main else "inherit"
                        ui.html(
                            f"<div><strong style='color:{name_color};'>{character['name']}</strong></div>"
                        )
                        ui.html(
                            f"<div class='app-muted'>{character['class_name']}</div>"
                        )

                    with ui.element("div").classes("character-col-stat"):
                        ui.html(f"<div><strong>{item_level_text}</strong></div>")
                        ui.html("<div class='app-muted'>Item Level</div>")

                    with ui.element("div").classes("character-col-stat"):
                        if not is_editing:
                            ui.html(f"<div><strong>{combat_power_text}</strong></div>")
                            ui.html("<div class='app-muted'>Combat Power</div>")
                        else:
                            power_input = ui.number(
                                "Combat Power",
                                value=ui_state["edit"]["power"]
                                if ui_state["edit"]["power"] is not None
                                else 0,
                            )
                            power_input.on(
                                "update:model-value",
                                lambda e: ui_state["edit"].__setitem__("power", e.args),
                            )
                            ui.html("<div class='app-muted'>Combat Power</div>")

                    with ui.element("div").classes("character-col-role"):
                        if not is_editing:
                            ui.html(f"<div><strong>{role_text}</strong></div>")

                        else:
                            role_select = ui.select(
                                ["dps", "sup"],
                                value=(ui_state["edit"]["role"] or "dps"),
                                label="Role",
                            )
                            role_select.on_value_change(
                                lambda e: ui_state["edit"].__setitem__("role", e.value),
                            )

                    with ui.row().classes("items-center gap-2"):
                        with ui.element("div").classes("character-col-actions"):
                            with ui.row().classes("items-center gap-2"):
                                if not is_editing:
                                    ui.button(
                                        icon="edit",
                                        on_click=lambda _e, c=character: (
                                            start_character_edit(
                                                c,
                                                ui_state,
                                            )
                                        ),
                                    ).classes("app-icon-btn")

                                    async def handle_character_refresh_click(
                                        _e, c=character["id"], m=character["member_id"]
                                    ):

                                        await refresh_character(m, c, ui_state)

                                    ui.button(
                                        icon="refresh",
                                        on_click=handle_character_refresh_click,
                                    ).classes("app-icon-btn")
                                    if not is_pending_character_delete:
                                        ui.button(
                                            icon="delete",
                                            on_click=lambda _e, c=character["id"], m=character["member_id"]: (
                                                start_character_delete(m, c, ui_state)
                                            ),
                                        ).classes("app-icon-btn")
                                    else:
                                        ui.button(
                                            icon="check",
                                            on_click=lambda _e, c=character["id"], m=character["member_id"]: (
                                                delete_character(
                                                    m,
                                                    c,
                                                    ui_state,
                                                )
                                            ),
                                        ).classes("app-icon-btn")
                                        ui.button(
                                            icon="close",
                                            on_click=lambda _e: cancel_character_delete(
                                                ui_state
                                            ),
                                        ).classes("app-icon-btn app-icon-btn-danger")

                                else:
                                    ui.button(
                                        icon="check",
                                        on_click=lambda _e,: save_character_edit(
                                            ui_state,
                                        ),
                                    ).classes("app-icon-btn")
                                    ui.button(
                                        icon="close",
                                        on_click=lambda _e,: cancel_character_edit(
                                            ui_state
                                        ),
                                    ).classes("app-icon-btn app-icon-btn-danger")
    with ui.element("div").classes("app-panel character-card"):
        character_name_input = ui.input("Name")

        async def handle_add_click(_e, m=member_id):
            try:
                await add_character(m, character_name_input, ui_state)
            except ValueError as exc:
                ui.notify(str(exc), color="negative")

        ui.button(
            icon="add",
            on_click=handle_add_click,
        ).classes("app-icon-btn")


def render_member_card(
    member,
    characters_by_member,
    latest_sync_by_member,
    ui_state,
):
    latest_sync = latest_sync_by_member.get(member["id"], "Not tracked")
    with ui.element("div").classes("app-panel member-card"):
        with ui.element("div").classes("app-panel-head"):
            render_member_header(member, characters_by_member, ui_state)

        render_member_meta(member, latest_sync, ui_state)

        with ui.element("div").classes("app-panel-body"):
            render_characters_section(member["id"], member.get("roster_name"), ui_state)


@ui.refreshable
def render_members(ui_state):

    try:
        page_data = get_members_page_data()
    except ValueError as exc:
        with app_shell("Members"):
            with ui.element("div").classes("app-panel"):
                with ui.element("div").classes("app-panel-body"):
                    ui.label(str(exc))
        return

    members = page_data["members"]
    characters_by_member = page_data["characters_by_member"]
    latest_sync_by_member = page_data["latest_sync_by_member"]

    if not members:
        with ui.element("div").classes("app-panel"):
            with ui.element("div").classes("app-panel-body"):
                ui.label("No members created yet.")
        return

    for member in members:
        render_member_card(
            member,
            characters_by_member,
            latest_sync_by_member,
            ui_state,
        )


@ui.page("/members")
def members_page():

    ui_state = {
        "edit": {
            "character_id": None,
            "member_id": None,
            "role": "",
            "power": None,
        },
        "member_edit": {
            "member_id": None,
            "display_name": "",
            "discord_name": "",
            "notes": "",
        },
        "delete_member_id": None,
        "delete_character": {
            "member_id": None,
            "character_id": None,
        },
        "expanded_members": set(),
        "main_picker_member_id": None,
    }

    with app_shell("Members", "Guild roster and imported character data"):
        with ui.element("div").classes("app-split"):
            with ui.element("div"):
                with ui.element("div").classes("app-panel"):
                    with ui.element("div").classes("app-panel-head"):
                        ui.html("<h2>Create Member</h2>")

                    with ui.element("div").classes("app-panel-body app-form"):
                        display_name = ui.input("Name")
                        discord_name = ui.input("Discord Name")
                        region = ui.input("Region")
                        world = ui.input("Server")
                        roster_name = ui.input("Roster Name")
                        notes = ui.textarea("Notes")
                        ui.button(
                            "Create Member",
                            on_click=lambda: create_member_from_form(
                                display_name,
                                discord_name,
                                region,
                                world,
                                roster_name,
                                notes,
                            ),
                        ).classes("app-button-primary")

            with ui.element("div"):
                render_members(ui_state)


def start_member_edit(member: dict, ui_state: dict):
    ui_state["member_edit"]["member_id"] = member["id"]
    ui_state["member_edit"]["display_name"] = member.get("display_name") or ""
    ui_state["member_edit"]["discord_name"] = member.get("discord_name") or ""
    ui_state["member_edit"]["notes"] = member.get("notes") or ""
    render_members.refresh(ui_state)


def cancel_member_edit(ui_state: dict):
    ui_state["member_edit"]["member_id"] = None
    ui_state["member_edit"]["display_name"] = ""
    ui_state["member_edit"]["discord_name"] = ""
    ui_state["member_edit"]["notes"] = ""
    render_members.refresh(ui_state)


def save_member_edit(ui_state: dict):
    mid = ui_state["member_edit"]["member_id"]
    if mid is None:
        return
    try:
        update_member_fields(
            mid,
            ui_state["member_edit"]["display_name"],
            ui_state["member_edit"]["discord_name"],
            ui_state["member_edit"]["notes"],
        )
    except ValueError as exc:
        ui.notify(str(exc), color="negative")
        return

    cancel_member_edit(ui_state)
    ui.notify("Member updated.", color="positive")


def start_member_delete(member_id: int, ui_state: dict):
    ui_state["delete_member_id"] = member_id
    render_members.refresh(ui_state)


def cancel_member_delete(ui_state: dict):
    ui_state["delete_member_id"] = None
    render_members.refresh(ui_state)


def start_character_delete(member_id: int, character_id: int, ui_state: dict):
    ui_state["delete_character"]["member_id"] = member_id
    ui_state["delete_character"]["character_id"] = character_id
    render_members.refresh(ui_state)


def cancel_character_delete(ui_state: dict):
    ui_state["delete_character"]["character_id"] = None
    ui_state["delete_character"]["member_id"] = None
    render_members.refresh(ui_state)


def delete_member(
    member_id: int,
    ui_state: dict,
):
    force_delete_member_record(member_id)
    render_members.refresh(ui_state)
    ui.notify("Member deleted. Related assignments were also removed.", color="warning")


def delete_character(
    member_id: int,
    character_id: int,
    ui_state: dict,
):
    force_delete_character_record(member_id, character_id)
    render_members.refresh(ui_state)
    ui.notify(
        "Character deleted. Related assignments were also removed.", color="warning"
    )


def create_member_from_form(
    display_name,
    discord_name,
    region,
    world,
    roster_name,
    notes,
):
    if not display_name.value:
        ui.notify("Enter a name first.", color="negative")
        return

    create_member_record(
        display_name.value or "",
        discord_name.value or "",
        region.value or "",
        world.value or "",
        roster_name.value or "",
        notes.value or "",
    )
    render_members.refresh()
    ui.notify("Member created.", color="positive")
