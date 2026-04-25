from typing import Any
from app.schemas import TopCharacter, RosterSearchResult
import httpx


API_URL = "https://lostark.bible/api/link/search"
REQUEST_TIMEOUT = 20

CLASS_NAME_MAP = {
    "arcana": "Arcanist",
    "battle_master": "Wardancer",
    "bard": "Bard",
    "berserker": "Berserker",
    "blaster": "Artillerist",
    "deathblade": "Deathblade",
    "demonic": "Shadowhunter",
    "destroyer": "Destroyer",
    "devil_hunter": "Deadeye",
    "gunslinger": "Gunslinger",
    "gunlancer": "Gunlancer",
    "hawkeye": "Sharpshooter",
    "holy_knight": "Paladin",
    "infighter": "Scrapper",
    "lance_master": "Glaivier",
    "paladin": "Paladin",
    "scouter": "Machinist",
    "scrapper": "Scrapper",
    "shadowhunter": "Shadowhunter",
    "sharpshooter": "Sharpshooter",
    "sorceress": "Sorceress",
    "soul_master": "Soulfist",
    "soulfist": "Soulfist",
    "force_master": "Soulfist",
    "striker": "Striker",
    "summoner": "Summoner",
    "wardancer": "Wardancer",
    "warlord": "Gunlancer",
    "artist": "Artist",
    "reaper": "Reaper",
    "machinist": "Machinist",
    "arcanist": "Arcanist",
    "glaivier": "Glaivier",
    "aeromancer": "Aeromancer",
    "slayer": "Slayer",
    "soul_eater": "Souleater",
    "breaker": "Breaker",
    "dragon_knight": "Guardian Knight",
}


def _map_class_name(class_name: str | None) -> str:
    if not class_name:
        return ""

    return CLASS_NAME_MAP.get(class_name, class_name)


def _format_top_characters(characters: list[dict[str, Any]]) -> list[TopCharacter]:
    formatted_characters = []

    for character in characters:
        combat_power = character.get("combat_power") or {}
        formatted_characters.append(
            TopCharacter(
                name=character.get("name", ""),
                class_name=_map_class_name(character.get("class")),
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
                matched_character_class=_map_class_name(matched_character.get("class")),
                matched_character_region=matched_character.get("region"),
                matched_character_server_name=matched_character.get("world"),
                total_characters=item.get("total_characters"),
                top_characters=_format_top_characters(item.get("top_characters") or []),
            )
        )

    return results


def _normalize_character_name(character_name: str) -> str:
    return character_name.strip().title()


async def search_rosters(region: str, character_name: str) -> list[RosterSearchResult]:
    normalized_name = _normalize_character_name(character_name)
    params = {"region": region, "name": normalized_name}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(API_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    return _format_roster_results(payload)
