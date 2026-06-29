from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from livekit.agents import ToolError, function_tool, RunContext
from parser import parse_result


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
    # Validate the timezone string before using it.
    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ToolError(f"Unknown timezone: {timezone}")

    # Build a structured payload the LLM can narrate naturally.
    now = datetime.now(tz)
    return {
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "timezone": timezone,
    }


@function_tool()
async def fetch_osmania_result(
    context: RunContext,
    roll_no: str,
) -> dict:
    """Fetch the Osmania University exam result for a CSE student at MJ College.

    Use this whenever the user asks for their exam result. The hall ticket is
    derived automatically from the CSE roll number (prefix 160422733).

    Args:
        roll_no: The trailing roll number of the student (e.g., "83" or "083"). Zero-padding is applied automatically.
    """
    # Build the full hall ticket: CSE prefix + zero-padded roll number.
    prefix = "160422733"
    raw = str(roll_no).strip()
    if raw.isdigit() and int(raw) < 100:
        suffix = raw.zfill(3)
    else:
        suffix = raw
    htno = f"{prefix}{suffix}"

    # Form-encoded POST body the JSP endpoint expects.
    url = "https://www.osmania.ac.in/res07/20260430.jsp"
    form = {
        "mbstatus": "SEARCH",
        "htno": htno,
        "Submit.x": "0",
        "Submit.y": "0",
    }

    # Let the caller know we're working on it.
    await context.session.say("Fetching the result...")

    # Fetch the page and parse the result table into a typed schema.
    async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
        response = await client.post(url, data=form)
        response.raise_for_status()
        result = parse_result(response.text, htno)
        return result.model_dump()
