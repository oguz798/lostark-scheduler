from dataclasses import asdict

import httpx

from app.db import get_connection,save_imported_roster
from app.services.lostark_bible import search_rosters

IMPORT_ROSTER_SERVICE_UNAVAILABLE = (
    "Roster import failed because the external roster service is unavailable."
)
IMPORT_ROSTER_NO_RESULTS = "No roster results were found for that import request."

SEARCH_ROSTER_SERVICE_UNAVAILABLE = (
    "Roster search failed because the external roster service is unavailable."
)

# Shared wrapper around lostark.bible calls to normalize network errors into user-safe ValueError messages.
async def search_member_rosters(
    region: str, character_name: str, service_unavailable_message: str
) -> list:
    try:
        return await search_rosters(region, character_name, enrich_raid_loadout=False)
    except httpx.HTTPError as exc:
        raise ValueError(service_unavailable_message) from exc

def _select_roster_for_import(results: list, roster_id: int) -> dict | None:
    result_dicts = [asdict(result) for result in results]
    return next(
        (result for result in result_dicts if result.get("roster_id") == roster_id),
        None,
    )


# Re-fetches search results and picks the selected roster_id to ensure import uses fresh API data.
async def prepare_member_import(region: str, name: str, roster_id: int) -> dict:
    results = await search_member_rosters(
        region, name, IMPORT_ROSTER_SERVICE_UNAVAILABLE
    )
    if not results:
        raise ValueError(IMPORT_ROSTER_NO_RESULTS)

    selected_roster = _select_roster_for_import(results, roster_id)
    if selected_roster is None:
        raise ValueError(
            "The selected roster could not be found anymore. Try searching again."
        )

    return selected_roster

def save_selected_roster(member_id: int, roster_data: dict) -> None:
    save_imported_roster(member_id, roster_data)


def get_search_members() -> list[dict]:
    with get_connection() as connection:
        member_rows = connection.execute(
            "SELECT id, display_name FROM members ORDER BY display_name ASC"
        ).fetchall()

    return [dict(row) for row in member_rows]

# Aggregates everything the Search page needs in one payload: roster candidates + local member list + error state.
async def get_search_page_data(
    region: str, name: str, error: str | None = None
) -> dict:
    results = []
    if not error:
        try:
            results = await search_member_rosters(
                region, name, SEARCH_ROSTER_SERVICE_UNAVAILABLE
            )
        except ValueError as exc:
            error = str(exc)

    return {
        "results": results,
        "region": region,
        "name": name,
        "members": get_search_members(),
        "error": error,
    }
