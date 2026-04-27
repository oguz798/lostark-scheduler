from urllib.parse import urlencode
from datetime import date, timedelta

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import (
    create_week,
    get_connection,
    create_scheduled_raid,
    create_raid_assignment,
)


router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _get_next_wednesday() -> str:
    today = date.today()
    days_until_wednesday = (2 - today.weekday()) % 7

    if days_until_wednesday == 0:
        days_until_wednesday = 7

    next_wednesday = today + timedelta(days=days_until_wednesday)

    return next_wednesday.isoformat()


@router.get("/weeks")
async def weeks(request: Request, message: str | None = None):
    with get_connection() as connection:
        week_rows = connection.execute(
            "SELECT * FROM weeks ORDER BY start_date DESC"
        ).fetchall()
    default_start_date = _get_next_wednesday()
    weeks = [dict(row) for row in week_rows]
    return templates.TemplateResponse(
        name="weeks.html",
        request=request,
        context={
            "request": request,
            "weeks": weeks,
            "message": message,
            "default_start_date": default_start_date,
        },
    )


@router.post("/weeks/create")
async def create_week_route(
    start_date: str = Form(...),
    notes: str = Form(""),
):
    notes = notes.strip()
    try:
        create_week(start_date, notes)
        query = urlencode({"message": "Week creation successful"})
        return RedirectResponse(url=f"/weeks?{query}", status_code=303)
    except Exception:
        query = urlencode({"message": "Week creation failed"})
        return RedirectResponse(url=f"/weeks?{query}", status_code=303)


@router.get("/weeks/{week_id}")
async def get_week(week_id: int, request: Request, message: str | None = None):
    with get_connection() as connection:
        week_rows = connection.execute(
            "SELECT * FROM weeks WHERE id = ?",
            (week_id,),
        ).fetchone()
        if not week_rows:
            query = urlencode(
                {
                    "message": "No week found.",
                }
            )
            return RedirectResponse(url=f"/weeks?{query}", status_code=303)
        raid_def_rows = connection.execute(
            "SELECT * FROM raid_definitions ORDER BY min_item_level DESC"
        ).fetchall()
        scheduled_rows = connection.execute(
            """SELECT
                scheduled_raids.id,
                scheduled_raids.week_id,
                scheduled_raids.raid_definition_id,
                scheduled_raids.day,
                scheduled_raids.group_number,
                scheduled_raids.start_time,
                scheduled_raids.notes,
                scheduled_raids.sort_order,
                raid_definitions.title AS raid_title,
                raid_definitions.difficulty AS raid_difficulty
            FROM scheduled_raids
            JOIN raid_definitions
                ON scheduled_raids.raid_definition_id = raid_definitions.id
            WHERE scheduled_raids.week_id = ?
            ORDER BY day ASC, sort_order ASC""",
            (week_id,),
        ).fetchall()
        character_rows = connection.execute(
            "SELECT * FROM characters WHERE is_active = 1 ORDER BY item_level DESC, name ASC"
        ).fetchall()
        assignments_rows = connection.execute(
            """
            SELECT
                scheduled_raid_assignments.id,
                scheduled_raid_assignments.scheduled_raid_id,
                scheduled_raid_assignments.character_id,
                scheduled_raid_assignments.slot_order,
                scheduled_raid_assignments.notes,
                characters.name AS character_name,
                characters.class_name,
                characters.item_level,
                characters.combat_role,
                characters.combat_power_score
            FROM scheduled_raid_assignments
            JOIN characters
                ON scheduled_raid_assignments.character_id = characters.id
            WHERE scheduled_raid_assignments.scheduled_raid_id IN (
                SELECT id
                FROM scheduled_raids
                WHERE week_id = ?
            )
            ORDER BY scheduled_raid_assignments.scheduled_raid_id ASC,
                     scheduled_raid_assignments.slot_order ASC
            """,
            (week_id,),
        ).fetchall()

        week = dict(week_rows)
        raid_definitions = [dict(row) for row in raid_def_rows]
        scheduled_raids = [dict(row) for row in scheduled_rows]
        characters = [dict(row) for row in character_rows]
        scheduled_raid_assignments = [dict(row) for row in assignments_rows]
        return templates.TemplateResponse(
            name="week_detail.html",
            request=request,
            context={
                "request": request,
                "week": week,
                "raid_definitions": raid_definitions,
                "scheduled_raids": scheduled_raids,
                "characters": characters,
                "scheduled_raid_assignments": scheduled_raid_assignments,
                "message": message,
            },
        )


@router.post("/weeks/{week_id}/raids/create")
async def create_scheduled_raid_route(
    week_id: int,
    raid_definition_id: int = Form(...),
    day: str = Form(...),
    group_number: int = Form(...),
    start_time: str | None = Form(""),
    notes: str = Form(""),
    sort_order: int = Form(...),
):
    notes = notes.strip()
    start_time = start_time or None
    try:
        create_scheduled_raid(
            week_id,
            raid_definition_id,
            day,
            group_number,
            start_time,
            notes,
            sort_order,
        )
        query = urlencode({"message": "Scheduled raid creation successful"})
        return RedirectResponse(url=f"/weeks/{week_id}?{query}", status_code=303)
    except Exception:
        query = urlencode({"message": "Scheduled raid creation failed"})
        return RedirectResponse(url=f"/weeks/{week_id}?{query}", status_code=303)


@router.post("/scheduled-raids/{scheduled_raid_id}/assignments/create")
async def create_assignemnt(
    scheduled_raid_id: int,
    week_id: int = Form(...),
    character_id: int = Form(...),
    slot_order: int = Form(...),
    notes: str = Form(""),
):
    notes = notes.strip()
    try:
        create_raid_assignment(scheduled_raid_id, character_id, slot_order, notes)
        query = urlencode({"message": "Assignment successful"})
        return RedirectResponse(url=f"/weeks/{week_id}?{query}", status_code=303)
    except Exception:
        query = urlencode({"message": "Assignment failed"})
        return RedirectResponse(url=f"/weeks/{week_id}?{query}", status_code=303)
