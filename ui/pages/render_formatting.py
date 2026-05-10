def get_role_class(role_text: str) -> str:
    if role_text in ("SUP", "SUPPORT"):
        return "app-slot-role--sup"
    if role_text == "DPS":
        return "app-slot-role--dps"

    return ""


def format_item_level(value) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return "-"

    if number.is_integer():
        return str(int(number))

    return f"{number:.2f}".rstrip("0").rstrip(".")


def format_combat_power(value) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return "-"

    if number.is_integer():
        return str(int(number))

    return f"{number:.2f}".rstrip("0").rstrip(".")