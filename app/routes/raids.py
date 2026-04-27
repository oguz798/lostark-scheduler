from urllib.parse import urlencode

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import create_raid_definition, get_connection


router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/raids")
async def raids(request: Request, message: str | None = None):
    with get_connection() as connection:
        raid_rows = connection.execute(
            "SELECT * FROM raid_definitions ORDER BY min_item_level DESC"
        ).fetchall()

    raids = [dict(row) for row in raid_rows]
    return templates.TemplateResponse(
        name="raids.html",
        request=request,
        context={"request": request, "raids": raids, "message": message},
    )


@router.post("/raids/create")
async def create_raid(
    title: str = Form(...),
    difficulty: str = Form(...),
    player_count: int = Form(...),
    min_item_level: float = Form(...),
    notes: str = Form(""),
):
    title = title.strip()
    difficulty = difficulty.strip()
    notes = notes.strip()
    try:
        create_raid_definition(title, difficulty, player_count, min_item_level, notes)
        query = urlencode({"message": "Raid creation successful"})
        return RedirectResponse(url=f"/raids?{query}", status_code=303)
    except Exception:
        query = urlencode({"message": "Raid creation failed"})
        return RedirectResponse(url=f"/raids?{query}", status_code=303)
