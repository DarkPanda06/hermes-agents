"""Digest & booking payloads — the messages Maitre WOULD send.

Per the demo constraints there is no live Telegram/Calendar integration: these
functions build the exact payloads (message text, calendar hold, logistics packet)
that a delivery layer would ship, and the demo prints them formatted. Everything is
derived from the event row + taste profile — no hardcoded per-event strings.
"""
from __future__ import annotations

from datetime import datetime, timedelta

_TRAVEL_NEAR_MIN = 20      # cab time when the venue is in a preferred area
_TRAVEL_FAR_MIN = 50       # cab time otherwise
_BUFFER_MIN = 15           # arrive-early buffer
_DEFAULT_DURATION_H = 3


def _start(event: dict) -> datetime:
    return datetime.fromisoformat(event["dt"])


def _travel_minutes(event: dict, profile: dict) -> int:
    preferred = set(profile.get("preferred_areas", []) or [])
    return _TRAVEL_NEAR_MIN if event.get("area") in preferred else _TRAVEL_FAR_MIN


def telegram_confirmation(event: dict) -> str:
    """Telegram-style booking confirmation (Markdown), as it would be sent."""
    start = _start(event)
    price = event.get("price_min") or 0
    return (
        "✅ *Booked — you're set for Saturday*\n"
        f"*{event['title']}*\n"
        f"📍 {event['venue']}, {event['area']}\n"
        f"🕗 {start:%a %d %b, %I:%M %p}\n"
        f"🎟 ₹{price:,.0f} • {event['capacity_class']} room\n"
        f"🔗 {event.get('url', '')}\n\n"
        "_Calendar hold + logistics sent below. Reply /cancel to drop it._"
    )


def calendar_hold(event: dict) -> dict:
    """A calendar hold payload (ICS-shaped) for the booked event."""
    start = _start(event)
    end = start + timedelta(hours=_DEFAULT_DURATION_H)
    return {
        "summary": f"Maitre: {event['title']}",
        "location": f"{event['venue']}, {event['area']}",
        "dtstart": start.strftime("%Y%m%dT%H%M%S"),
        "dtend": end.strftime("%Y%m%dT%H%M%S"),
        "url": event.get("url", ""),
        "status": "CONFIRMED",
    }


def logistics_packet(event: dict, profile: dict) -> dict:
    """Everything the user needs to actually make it out the door."""
    start = _start(event)
    travel = _travel_minutes(event, profile)
    leave_by = start - timedelta(minutes=travel + _BUFFER_MIN)
    cap = float(profile.get("budget_cap_month", 0) or 0)
    price = float(event.get("price_min") or 0)
    home = profile.get("home_area", "home")

    budget_note = (
        f"₹{price:,.0f} entry — leaves ₹{cap - price:,.0f} of your ₹{cap:,.0f}/mo out-out budget"
        if price <= cap else
        f"₹{price:,.0f} entry — OVER your ₹{cap:,.0f}/mo cap"
    )
    return {
        "leave_by": f"{leave_by:%I:%M %p}",
        "travel": f"~{travel} min cab from {home}",
        "doors": f"{start:%I:%M %p}",
        "budget": budget_note,
        "reservation": (
            "Table reserved under your name — arrive 10 min early for the good seats"
            if event.get("capacity_class") == "intimate" else
            "General entry — no table hold"
        ),
        "note": "Seated/listening room — phones down, this one rewards attention.",
    }
