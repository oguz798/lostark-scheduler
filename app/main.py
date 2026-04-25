from urllib.parse import urlencode
from datetime import datetime

import httpx
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.lostark_bible import search_rosters
from app.db import (
    init_db,
    get_connection,
    save_imported_roster,
    delete_member,
    current_timestamp,
)
from dataclasses import asdict
from fastapi.staticfiles import StaticFiles


app = FastAPI(title="Lost Ark Scheduler")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def format_timestamp(value: str | None) -> str:
    if not value:
        return "Not tracked"

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value

    return parsed.strftime("%d %b %Y, %H:%M UTC")


def _select_refresh_roster(results: list, roster_name: str):
    normalized_roster_name = roster_name.strip().casefold()
    for result in results:
        matched_name = (result.matched_character_name or "").strip().casefold()
        if matched_name == normalized_roster_name:
            return asdict(result)

    return asdict(results[0]) if results else None


@app.on_event("startup")
def startup():
    init_db()


@app.get("/members")
async def members(request: Request, message: str | None = None):
    with get_connection() as connection:
        member_rows = connection.execute(
            "SELECT * FROM members ORDER BY display_name ASC"
        ).fetchall()
        character_rows = connection.execute(
            "SELECT * FROM characters ORDER BY item_level DESC, name ASC"
        ).fetchall()
    members = []
    for row in member_rows:
        member = dict(row)
        member["created_at_formatted"] = format_timestamp(member.get("created_at"))
        members.append(member)
    characters = [dict(row) for row in character_rows]

    characters_by_member = {}
    latest_sync_by_member = {}

    for character in characters:
        member_id = character["member_id"]
        characters_by_member.setdefault(member_id, []).append(character)
        last_synced_at = character.get("last_synced_at")
        if last_synced_at and (
            member_id not in latest_sync_by_member
            or last_synced_at > latest_sync_by_member[member_id]
        ):
            latest_sync_by_member[member_id] = last_synced_at

    latest_sync_by_member = {
        member_id: format_timestamp(timestamp)
        for member_id, timestamp in latest_sync_by_member.items()
    }

    return templates.TemplateResponse(
        name="members.html",
        request=request,
        context={
            "request": request,
            "members": members,
            "characters_by_member": characters_by_member,
            "latest_sync_by_member": latest_sync_by_member,
            "message": message,
        },
    )


@app.post("/members/create")
async def create_members(
    display_name: str = Form(...),
    discord_name: str = Form(""),
    region: str = Form(""),
    world: str = Form(""),
    roster_name: str = Form(""),
    notes: str = Form(""),
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO members (
                display_name,
                discord_name,
                region,
                world,
                roster_name,
                notes,
                created_at
            )
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                display_name,
                discord_name,
                region,
                world,
                roster_name,
                notes,
                current_timestamp(),
            ),
        )
    return RedirectResponse(url="/members", status_code=303)


@app.post("/members/import")
async def import_roster(
    member_id: int = Form(...),
    region: str = Form(...),
    name: str = Form(...),
    roster_id: int = Form(...),
):
    try:
        results = await search_rosters(region, name)
    except httpx.HTTPError:
        query = urlencode(
            {
                "region": region,
                "name": name,
                "error": "Roster import failed because the external roster service is unavailable.",
            }
        )
        return RedirectResponse(url=f"/search?{query}", status_code=303)
    if not results:
        query = urlencode(
            {
                "region": region,
                "name": name,
                "error": "No roster results were found for that import request.",
            }
        )
        return RedirectResponse(url=f"/search?{query}", status_code=303)

    result_dicts = [asdict(result) for result in results]
    selected_roster = next(
        (result for result in result_dicts if result.get("roster_id") == roster_id),
        None,
    )
    if selected_roster is None:
        query = urlencode(
            {
                "region": region,
                "name": name,
                "error": "The selected roster could not be found anymore. Try searching again.",
            }
        )
        return RedirectResponse(url=f"/search?{query}", status_code=303)

    save_imported_roster(member_id, selected_roster)
    return RedirectResponse(url="/members", status_code=303)


@app.post("/members/{member_id}/refresh")
async def refresh_member_roster(member_id: int):
    with get_connection() as connection:
        member_row = connection.execute(
            "SELECT id, region, roster_name FROM members WHERE id = ?",
            (member_id,),
        ).fetchone()

    if member_row is None:
        query = urlencode({"message": "Member could not be found for refresh."})
        return RedirectResponse(url=f"/members?{query}", status_code=303)

    member = dict(member_row)
    region = (member.get("region") or "").strip()
    roster_name = (member.get("roster_name") or "").strip()

    if not region or not roster_name:
        query = urlencode(
            {"message": "This member needs a saved region and roster name before it can be refreshed."}
        )
        return RedirectResponse(url=f"/members?{query}", status_code=303)

    try:
        results = await search_rosters(region, roster_name)
    except httpx.HTTPError:
        query = urlencode(
            {"message": "Roster refresh failed because the external roster service is unavailable."}
        )
        return RedirectResponse(url=f"/members?{query}", status_code=303)

    selected_roster = _select_refresh_roster(results, roster_name)
    if selected_roster is None:
        query = urlencode(
            {"message": "No matching roster could be found for this member refresh."}
        )
        return RedirectResponse(url=f"/members?{query}", status_code=303)

    save_imported_roster(member_id, selected_roster)
    return RedirectResponse(url="/members", status_code=303)


@app.post("/members/{member_id}/delete")
async def remove_member(member_id: int):
    delete_member(member_id)
    return RedirectResponse(url="/members", status_code=303)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        name="index.html", request=request, context={"request": request}
    )


@app.get("/search")
async def search(request: Request, region: str, name: str, error: str | None = None):
    results = []
    if not error:
        try:
            results = await search_rosters(region, name)
        except httpx.HTTPError:
            error = "Roster search failed because the external roster service is unavailable."

    with get_connection() as connection:
        member_rows = connection.execute(
            "SELECT id, display_name FROM members ORDER BY display_name ASC"
        ).fetchall()
    members = [dict(row) for row in member_rows]

    return templates.TemplateResponse(
        name="search.html",
        request=request,
        context={
            "request": request,
            "results": results,
            "region": region,
            "name": name,
            "members": members,
            "error": error,
        },
    )
