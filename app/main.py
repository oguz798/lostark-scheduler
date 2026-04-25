from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.lostark_bible import search_rosters
from app.db import (
    init_db,
    get_connection,
    save_imported_roster,
    delete_member,
    delete_character,
)
from dataclasses import asdict
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Lost Ark Scheduler")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/members")
async def members(request: Request):
    with get_connection() as connection:
        member_rows = connection.execute(
            "SELECT * FROM members ORDER BY display_name ASC"
        ).fetchall()
        character_rows = connection.execute(
            "SELECT * FROM characters ORDER BY item_level DESC, name ASC"
        ).fetchall()
    members = [dict(row) for row in member_rows]
    characters = [dict(row) for row in character_rows]

    characters_by_member = {}

    for character in characters:
        member_id = character["member_id"]
        characters_by_member.setdefault(member_id, []).append(character)
    return templates.TemplateResponse(
        name="members.html",
        request=request,
        context={
            "request": request,
            "members": members,
            "characters_by_member": characters_by_member,
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
                notes
            )
            VALUES(?,?,?,?,?,?)
            """,
            (display_name, discord_name, region, world, roster_name, notes),
        )
    return RedirectResponse(url="/members", status_code=303)


@app.post("/members/import")
async def import_roster(
    member_id: int = Form(...),
    region: str = Form(...),
    name: str = Form(...),
    roster_id: int = Form(...),
):
    results = await search_rosters(region, name)

    if not results:
        return {"ok": False, "error": "No roster results found."}
    result_dicts = [asdict(result) for result in results]
    selected_roster = next(
        (result for result in result_dicts if result.get("roster_id") == roster_id),
        None,
    )
    if selected_roster is None:
        return {"ok": False, "error": "Selected roster could not be found."}

    save_imported_roster(member_id, selected_roster)
    return RedirectResponse(url="/members", status_code=303)


@app.post("/members/{member_id}/delete")
async def remove_member(member_id: int):
    delete_member(member_id)
    return RedirectResponse(url="/members", status_code=303)


@app.post("/characters/{character_id}/delete")
async def remove_character(character_id: int):
    delete_character(character_id)
    return RedirectResponse(url="/members", status_code=303)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        name="index.html", request=request, context={"request": request}
    )


@app.get("/search")
async def search(request: Request, region: str, name: str):
    results = await search_rosters(region, name)

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
        },
    )
