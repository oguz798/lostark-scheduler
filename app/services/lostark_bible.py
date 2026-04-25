from typing import Any
from app.schemas import TopCharacter, RosterSearchResult
import httpx


API_URL = "https://lostark.bible/api/link/search"
REQUEST_TIMEOUT = 20


def _format_top_characters(characters: list[dict[str, Any]]) -> list[TopCharacter]:
    formatted_characters = []

    for character in characters:
        combat_power = character.get("combat_power") or {}
        formatted_characters.append(
            TopCharacter(
                name=character.get("name", ""),
                class_name=character.get("class", ""),
                item_level=character.get("item_level"),
                combat_power_id=combat_power.get("id"),
                combat_power_score=combat_power.get("score"),
                region=character.get("region"),
                server_name=character.get("world"),
            )
        )

    return formatted_characters


def _format_roster_results(payload: list[dict[str, Any]]) -> list[RosterSearchResult]:
    results = []

    for item in payload:
        matched_character = item.get("matched_character") or {}
        results.append(
            RosterSearchResult(
                roster_id=item.get("id"),
                matched_character_name=matched_character.get("name", ""),
                matched_character_class=matched_character.get("class"),
                matched_character_region=matched_character.get("region"),
                matched_character_server_name=matched_character.get("world"),
                total_characters=item.get("total_characters"),
                top_characters=_format_top_characters(item.get("top_characters") or []),
            )
        )

    return results


async def search_rosters(region: str, character_name: str) -> list[RosterSearchResult]:
    params = {"region": region, "name": character_name}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(API_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    print(payload)
    return _format_roster_results(payload)
