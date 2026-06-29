from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from livekit.agents import ToolError, function_tool, RunContext


@function_tool()
async def get_current_time(
    context: RunContext,
    timezone: str = "UTC",
) -> dict:
    """Get the current date and time in a specific timezone.

    Use this whenever the user asks about the current time, date, day, or "what time is it".
    If the user does not specify a timezone, default to UTC.

    Args:
        timezone: IANA timezone name (e.g., "UTC", "America/New_York", "Europe/London", "Asia/Tokyo").
    """
    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ToolError(f"Unknown timezone: {timezone}")

    now = datetime.now(tz)
    return {
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "timezone": timezone,
    }
