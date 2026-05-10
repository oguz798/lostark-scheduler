from nicegui import ui

from app.schemas.week_plan import (
    PlanGroup,
    PlanRaidBlock,
    WeekPlanContext,
)
from ui.pages.week_plan.actions import (
    add_raid_group_action,
    toggle_assignment_drawer,
    start_pool_character_drag,
)
from ui.pages.week_plan.render_assignments import render_assignment_sidebar
from ui.pages.week_plan.render_groups import render_group_grid


def render_raid_cards(
    context: WeekPlanContext,
    ui_state: dict,
    refresh_week,
) -> None:
    with ui.element("div").classes("app-raids-wrap"):
        with ui.element("div").classes("app-raids-stack"):
            for raid_name, raid_data in sorted(
                context.raid_blocks.items(),
                key=lambda item: item[1].min_item_level,
                reverse=True,
            ):
                render_raid_card(
                    raid_name,
                    raid_data,
                    context,
                    ui_state,
                    refresh_week,
                )


def render_raid_card(
    raid_name: str,
    raid_data: PlanRaidBlock,
    context: WeekPlanContext,
    ui_state: dict,
    refresh_week,
) -> None:
    raid_key = raid_name
    groups = raid_data.groups
    item_level_text = (
        f"{raid_data.min_item_level:.0f}" if raid_data.min_item_level else "-"
    )
    is_raid_open = raid_key in ui_state["expanded_raids"]
    is_assignment_open = ui_state["open_assignment_raid_name"] == raid_name
    shell_classes = "app-panel app-plan-panel app-raid-shell"
    if is_assignment_open:
        shell_classes += " app-raid-shell-open"

    with ui.element("div").classes(shell_classes):
        with ui.expansion(
            f"{raid_name} · {item_level_text}",
            value=is_raid_open,
        ).classes("app-raid-expansion") as raid_expansion:
            raid_expansion.on_value_change(
                lambda e, key=raid_key: _sync_expanded_raid(ui_state, key, e.value)
            )

            render_raid_toolbar(raid_name, raid_data, groups, ui_state, refresh_week)

            if not groups:
                ui.html("<div class='app-muted'>No groups created yet.</div>")
                return

            body_class = (
                "app-raid-body-grid app-raid-body-grid-open"
                if is_assignment_open
                else "app-raid-body-grid app-raid-body-grid-closed"
            )

            with ui.element("div").classes(body_class):
                if is_assignment_open:
                    with ui.element("div").classes("app-raid-body-left"):
                        render_assignment_sidebar(
                            raid_name,
                            raid_data,
                            context,
                            ui_state,
                            start_pool_character_drag,
                            refresh_week,
                        )

                with ui.element("div").classes("app-raid-body-right"):
                    render_group_grid(raid_name, groups, ui_state, refresh_week)

            render_raid_note(raid_key, ui_state)


def render_raid_toolbar(
    raid_name: str,
    raid_data: PlanRaidBlock,
    groups: dict[str, PlanGroup],
    ui_state: dict,
    refresh_week,
) -> None:
    with ui.row().classes("items-center gap-2"):
        ui.button(
            icon="add",
            on_click=lambda _e, rd=raid_data: add_raid_group_action(
                rd,
                ui_state,
                refresh_week,
            ),
        ).classes("app-icon-btn")

        if groups:
            ui.button(
                "Eligible",
                icon="group",
                on_click=lambda _e, rn=raid_name: toggle_assignment_drawer(
                    rn,
                    ui_state,
                    refresh_week,
                ),
            ).classes("app-icon-btn")


def render_raid_note(raid_key: str, ui_state: dict) -> None:
    ui.input(
        "Raid Note",
        value=ui_state["raid_notes"].get(raid_key, ""),
    ).classes("w-full app-raid-note").props("dense").on(
        "update:model-value",
        lambda e, k=raid_key: ui_state["raid_notes"].__setitem__(k, e.args or ""),
    )


def _sync_expanded_raid(ui_state: dict, key: str, is_open: bool) -> None:
    if is_open:
        ui_state["expanded_raids"].add(key)
    else:
        ui_state["expanded_raids"].discard(key)
