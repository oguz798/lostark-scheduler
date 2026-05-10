def check_availability_for_group_time(
    availability_days: dict,
    group_day: str,
    group_start_time: str | None,
) -> tuple[bool, str]:

    day_availability = availability_days.get(group_day)

    if not day_availability:
        return True, ""

    status = (day_availability.get("status") or "available").lower()
    available_after = day_availability.get("available_after") or ""

    if status == "available":
        return True, ""
    if status == "unavailable":
        return False, f"Member is unavailable on {group_day}"
    if status == "after":
        if not group_start_time:
            return True, ""
        if not available_after:
            return True, ""
        if group_start_time < available_after:
            return False, f"Member is only available after {available_after}"

    return True, ""
