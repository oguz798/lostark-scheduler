import asyncio
import re
from urllib.parse import quote
from typing import Any

import httpx

from app.schemas import TopCharacter, RosterSearchResult

SITE_URL = "https://lostark.bible"
API_URL = "https://lostark.bible/api/link/search"

REQUEST_TIMEOUT = 20
# Keep enrichment code available for future use, but disable it by default for current API/policy constraints.
ALLOW_RAID_LOADOUT_ENRICH = False

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
    "infighter_male": "Breaker",
    "lance_master": "Glaivier",
    "paladin": "Paladin",
    "scouter": "Machinist",
    "scrapper": "Scrapper",
    "shadowhunter": "Shadowhunter",
    "sharpshooter": "Sharpshooter",
    "elemental_master": "Sorceress",
    "soul_master": "Soulfist",
    "soulfist": "Soulfist",
    "force_master": "Soulfist",
    "striker": "Striker",
    "summoner": "Summoner",
    "wardancer": "Wardancer",
    "warlord": "Gunlancer",
    "yinyangshi": "Artist",
    "reaper": "Reaper",
    "machinist": "Machinist",
    "arcanist": "Arcanist",
    "glaivier": "Glaivier",
    "weather_artist": "Aeromancer",
    "slayer": "Slayer",
    "soul_eater": "Souleater",
    "dragon_knight": "Guardianknight",
    "holyknight_female": "Valkyrie",
    "alchemist": "Wildsoul",
}


def _map_class_name(class_name: str | None) -> str:
    if not class_name:
        return ""

    return CLASS_NAME_MAP.get(class_name, class_name)


def _map_combat_role(combat_power_id: int | None) -> str | None:
    if combat_power_id == 1:
        return "dps"
    elif combat_power_id == 2:
        return "support"
    else:
        return None


async def _format_top_characters(
    characters: list[dict[str, Any]], enrich_raid_loadout: bool = False
) -> list[TopCharacter]:
    # Enriched raid-loadout scraping path is retained for future access but normally disabled by caller/flag.
    formatted_characters = []

    if not enrich_raid_loadout:
        for character in characters:
            combat_power = character.get("combat_power") or {}
            combat_power_id = combat_power.get("id")
            formatted_characters.append(
                TopCharacter(
                    name=character.get("name", ""),
                    class_name=_map_class_name(character.get("class")),
                    item_level=character.get("item_level"),
                    combat_power_id=combat_power_id,
                    combat_role=_map_combat_role(combat_power_id),
                    combat_power_score=combat_power.get("score"),
                    region=character.get("region"),
                    server_name=character.get("world"),
                )
            )
        return formatted_characters

    fetch_tasks = [
        _fetch_character_page_html(
            character.get("region", ""), character.get("name", "")
        )
        for character in characters
    ]
    html_results = await asyncio.gather(*fetch_tasks)
    for character, html_text in zip(characters, html_results):
        combat_power = character.get("combat_power") or {}
        combat_power_id = combat_power.get("id")
        raid_loadout_score = _extract_raid_loadout_combat_power(html_text)
        combat_power_score = (
            raid_loadout_score
            if raid_loadout_score is not None
            else combat_power.get("score")
        )
        formatted_characters.append(
            TopCharacter(
                name=character.get("name", ""),
                class_name=_map_class_name(character.get("class")),
                item_level=character.get("item_level"),
                combat_power_id=combat_power_id,
                combat_role=_map_combat_role(combat_power_id),
                combat_power_score=combat_power_score,
                region=character.get("region"),
                server_name=character.get("world"),
            )
        )
    return formatted_characters


async def _format_roster_results(
    payload: list[dict[str, Any]], enrich_raid_loadout: bool = False
) -> list[RosterSearchResult]:
    results = []

    for item in payload:
        matched_character = item.get("matched_character") or {}
        matched_combat_power = matched_character.get("combat_power") or {}
        matched_role = _map_combat_role(matched_combat_power.get("id"))
        matched_combat_score = matched_combat_power.get("score")
        results.append(
            RosterSearchResult(
                roster_id=item.get("id"),
                matched_character_name=matched_character.get("name", ""),
                matched_character_class=_map_class_name(matched_character.get("class")),
                matched_character_region=matched_character.get("region"),
                matched_character_server_name=matched_character.get("world"),
                matched_character_item_level=matched_character.get("item_level"),
                matched_character_combat_power_id=matched_combat_power.get("id"),
                matched_character_combat_role=matched_role,
                matched_character_combat_power=matched_combat_score,
                total_characters=item.get("total_characters"),
                top_characters=await _format_top_characters(
                    item.get("top_characters") or [], enrich_raid_loadout
                ),
            )
        )

    return results


def _normalize_character_name(character_name: str) -> str:
    return character_name.strip().title()


async def search_rosters(
    region: str, character_name: str, enrich_raid_loadout: bool = False
) -> list[RosterSearchResult]:
    # Enrichment requests are gated so current production behavior remains API-search only.
    enrich_raid_loadout = enrich_raid_loadout and ALLOW_RAID_LOADOUT_ENRICH
    normalized_name = _normalize_character_name(character_name)
    params = {"region": region, "name": normalized_name}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(API_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    return await _format_roster_results(
        payload, enrich_raid_loadout=enrich_raid_loadout
    )


async def _fetch_character_page_html(region: str, character_name: str) -> str | None:
    normalized_name = _normalize_character_name(character_name)
    encoded_name = quote(normalized_name)

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            response = await client.get(f"{SITE_URL}/character/{region}/{encoded_name}")
            response.raise_for_status()

            return response.text
        except httpx.HTTPError:
            return None


def _extract_raid_loadout_combat_power(html_text: str | None) -> float | None:
    if not html_text:
        return None

    match = re.search(
        r'classification:"most_recent_raid".*?combatPower:\{id:\d+,score:([0-9.]+)\}',
        html_text,
        re.DOTALL,
    )
    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None
