DPS_ROLE = "DPS"
SUPPORT_ROLE = "SUP"
SUPPORT_SLOT_ORDERS = {4, 8}


def normalize_combat_role(value: str | None) -> str:
    role = (value or "").strip().upper()

    if role == "SUPPORT":
        return SUPPORT_ROLE

    return role


def get_required_slot_role(slot_order: int) -> str:
    return SUPPORT_ROLE if int(slot_order) in SUPPORT_SLOT_ORDERS else DPS_ROLE
