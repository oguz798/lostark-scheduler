from dataclasses import dataclass, field


@dataclass
class TopCharacter:
    name: str
    class_name: str
    region: str | None
    server_name: str | None
    item_level: float | None
    combat_power_id: int | None
    combat_role: str | None
    combat_power_score: float | None


@dataclass
class RosterSearchResult:
    roster_id: int | None
    matched_character_name: str | None
    matched_character_class: str | None
    matched_character_region: str | None
    matched_character_server_name: str | None
    matched_character_item_level: float | None
    matched_character_combat_power_id: int | None
    matched_character_combat_role: str | None
    matched_character_combat_power: float | None
    total_characters: int | None
    top_characters: list[TopCharacter]
