from dataclasses import dataclass, field


@dataclass
class PlanAssignment:
    assignment_id: int
    raid_group_id: int
    character_id: int
    member_id: int
    slot_order: int
    character_name: str
    class_name: str
    member_name: str
    combat_role: str
    item_level: float | None
    combat_power_score: float | None


@dataclass
class PlanGroup:
    raid_group_id: int
    raid_id: int
    group_number: int
    day: str
    start_time: str | None
    sort_order: int
    notes: str
    parties: dict[str, list[PlanAssignment | None]]


@dataclass
class PlanRaidBlock:
    raid_id: int
    min_item_level: float
    groups: dict[str, PlanGroup] = field(default_factory=dict)


@dataclass
class ScheduleRow:
    day: str
    time_text: str
    raid_text: str
    notes: str


@dataclass
class PlanCharacter:
    id: int
    member_id: int
    member_name: str
    name: str
    class_name: str
    combat_role: str | None
    item_level: float | None
    combat_power_score: float | None
    is_active: bool


@dataclass
class CharacterPoolMember:
    member_id: int
    member_name: str
    characters: list[PlanCharacter] = field(default_factory=list)


@dataclass
class WeekPlanContext:
    week: dict
    raids: list[dict]

    character_pool: dict[int, CharacterPoolMember]
    raid_blocks: dict[str, PlanRaidBlock]
    schedule_rows: list[ScheduleRow]
    member_availability_rows: list[dict]

    characters_by_id: dict[int, PlanCharacter]
    groups_by_id: dict[int, PlanGroup]
    member_availability_by_id: dict[int, dict]
    assignments_by_id: dict[int, PlanAssignment]
    assignments_by_group_slot: dict[tuple[int, int], PlanAssignment]
