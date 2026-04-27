import httpx
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import get_connection, init_db
from app.routes.members import router as members_router
from app.routes.raids import router as raids_router
from app.routes.weeks import router as weeks_router
from app.services.lostark_bible import search_rosters


app = FastAPI(title="Lost Ark Scheduler")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.include_router(raids_router)
app.include_router(members_router)
app.include_router(weeks_router)


@app.on_event("startup")
def startup():
    init_db()


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
