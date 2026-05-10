from nicegui import ui

from app.schemas.week_plan import (
    CharacterPoolMember,
    PlanCharacter,
    PlanRaidBlock,
    WeekPlanContext,
)
from ui.pages.week_plan.data import build_eligible_character_pool
from ui.pages.render_formatting import (
    get_role_class,
    format_combat_power,
    format_item_level,
)


def render_assignment_sidebar(
    raid_name: str,
    raid_data: PlanRaidBlock,
    context: WeekPlanContext,
    ui_state: dict,
    on_character_drag_start,
    refresh_week,
) -> None:
    is_open = ui_state["open_assignment_raid_name"] == raid_name
    if not is_open:
        return

    min_item_level = raid_data.min_item_level

    with ui.element("div").classes("app-assignment-sidebar app-panel"):
        with ui.element("div").classes("app-panel-head"):
            ui.html(
                f"<h2>{raid_name}</h2>"
                f"<div class='app-muted'>Eligible characters · {min_item_level:.0f}+</div>"
            )

        with ui.element("div").classes("app-panel-body"):
            filters = ui_state["assignment_filters"]

            with ui.row().classes("app-assignment-filters w-full items-end gap-2"):
                search_input = (
                    ui.input(
                        "Search",
                        value=filters["search_query"],
                        placeholder="character or class",
                    )
                    .classes("flex-1")
                    .props("dense outlined")
                )
                search_input.on_value_change(
                    lambda e, f=filters: f.__setitem__(
                        "search_query",
                        (e.value or "").strip(),
                    )
                )

                search_input.on("keydown.enter", lambda _e: refresh_week(ui_state))
                search_input.on("blur", lambda _e: refresh_week(ui_state))

                ui.select(
                    ["ALL", "DPS", "SUP"],
                    value=filters["role_filter"],
                    label="Role",
                ).classes("w-28").props("dense outlined").on_value_change(
                    lambda e, f=filters: (
                        f.__setitem__("role_filter", (e.value or "ALL").upper()),
                        refresh_week(ui_state),
                    )
                )

                ui.checkbox(
                    "Show assigned",
                    value=filters["show_assigned"],
                ).on_value_change(
                    lambda e, f=filters: (
                        f.__setitem__("show_assigned", bool(e.value)),
                        refresh_week(ui_state),
                    )
                ).classes("pt-2")

            eligible_members, assigned_ids = build_eligible_character_pool(
                context, raid_data, filters
            )

            visible_member_count = 0
            with ui.element("div").classes("app-assignment-member-grid"):
                for member_data, eligible_characters in eligible_members:
                    visible_member_count += 1
                    render_eligible_member(
                        member_data,
                        eligible_characters,
                        assigned_ids,
                        ui_state,
                        on_character_drag_start,
                    )

            if visible_member_count == 0:
                ui.html(
                    "<div class='app-assignment-empty'>"
                    "No eligible characters match these filters."
                    "</div>"
                )


def render_eligible_member(
    member_data,
    eligible_characters,
    assigned_ids: set[int],
    ui_state: dict,
    on_character_drag_start,
) -> None:
    member_key = member_data.member_name
    is_member_open = member_key in ui_state["expanded_eligible_members"]

    with ui.expansion(
        f"{member_data.member_name} ({len(eligible_characters)})",
        value=is_member_open,
    ).classes("w-full") as eligible_expansion:
        eligible_expansion.on_value_change(
            lambda e, key=member_key: _sync_expanded_eligible_member(
                ui_state,
                key,
                e.value,
            )
        )

        with ui.element("div").classes("app-assignment-character-list"):
            for character in eligible_characters:
                role_text = (character.combat_role or "-").upper()
                role_class = get_role_class(role_text)
                item_level_text = format_item_level(character.item_level)
                is_assigned = int(character.id) in assigned_ids

                row_classes = "app-assignment-character-pill"
                if is_assigned:
                    row_classes += " app-assignment-character-pill-assigned"

                with (
                    ui.element("div")
                    .classes(row_classes)
                    .props("draggable=true") as drag_card
                ):
                    ui.html(
                        f"<div class='app-assignment-character-pill-content'>"
                        f"<span class='app-assignment-character-class'>{character.class_name}</span>"
                        f"<span class='app-assignment-character-ilvl'>{item_level_text}</span>"
                        f"<span class='app-assignment-character-role {role_class}'>{role_text}</span>"
                        f"</div>"
                    )
                    with ui.tooltip().classes("app-slot-tooltip"):
                        ui.html(_build_pool_hover_html(character))
                drag_card.on(
                    "dragstart",
                    lambda _e, c=character: on_character_drag_start(c, ui_state),
                )


def _sync_expanded_eligible_member(
    ui_state: dict,
    key: str,
    is_open: bool,
) -> None:
    if is_open:
        ui_state["expanded_eligible_members"].add(key)
    else:
        ui_state["expanded_eligible_members"].discard(key)


def _build_pool_hover_html(character) -> str:
    ilvl = format_item_level(character.item_level)
    cp = format_combat_power(character.combat_power_score)
    role = (character.combat_role or "-").upper()
    char_name = character.name or "-"

    return (
        f"<div><strong>Character:</strong> {char_name}</div>"
        f"<div><strong>iLvl:</strong> {ilvl}</div>"
        f"<div><strong>CP:</strong> {cp}</div>"
        f"<div><strong>Role:</strong> {role}</div>"
    )
