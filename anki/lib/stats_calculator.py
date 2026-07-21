#!/usr/bin/env python3
"""Pure calculations for deterministic Anki statistics reports."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo


class StatsDataError(RuntimeError):
    """Raised when AnkiConnect returns an invalid statistics payload."""


def history_start_id(timezone: str, now: datetime | None = None) -> int:
    """Return the inclusive review timestamp for two completed seven-day windows."""
    tz = ZoneInfo(timezone)
    current = _localized_now(tz, now)
    report_date = current.date() - timedelta(days=1)
    comparison_start = report_date - timedelta(days=13)
    start = datetime.combine(comparison_start, time.min, tzinfo=tz)
    return int(start.timestamp() * 1000)


def calculate_history(
    rows: Iterable[object], timezone: str, now: datetime | None = None
) -> dict[str, Any]:
    """Aggregate Anki review-log rows into yesterday and two seven-day windows."""
    tz = ZoneInfo(timezone)
    current = _localized_now(tz, now)
    report_date = current.date() - timedelta(days=1)
    primary_dates = [
        report_date - timedelta(days=offset) for offset in range(6, -1, -1)
    ]
    comparison_dates = [
        report_date - timedelta(days=offset) for offset in range(13, 6, -1)
    ]
    first_date = comparison_dates[0]
    end_date = report_date + timedelta(days=1)

    events: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, (list, tuple)) or len(raw) < 9:
            raise StatsDataError("AnkiConnect returned an invalid cardReviews row.")
        try:
            timestamp_ms = int(raw[0])
            card_id = int(raw[1])
            rating = int(raw[3])
            duration_ms = max(0, int(raw[7]))
        except (TypeError, ValueError) as exc:
            raise StatsDataError("AnkiConnect returned a non-numeric review row.") from exc
        if rating not in {1, 2, 3, 4}:
            continue
        local_date = datetime.fromtimestamp(timestamp_ms / 1000, tz).date()
        if first_date <= local_date < end_date:
            events.append(
                {
                    "timestamp_ms": timestamp_ms,
                    "card_id": card_id,
                    "rating": rating,
                    "duration_ms": duration_ms,
                    "date": local_date,
                }
            )

    events.sort(key=lambda event: (event["timestamp_ms"], event["card_id"]))
    primary = _period(events, set(primary_dates))
    previous = _period(events, set(comparison_dates))
    yesterday = _period(events, {report_date})
    daily = []
    for day in primary_dates:
        values = _period(events, {day})
        values["date"] = day.isoformat()
        daily.append(values)

    primary["days_studied"] = sum(day["answers"] > 0 for day in daily)
    primary["average_answers"] = round(primary["answers"] / 7)
    return {
        "timezone": timezone,
        "report_date": report_date.isoformat(),
        "yesterday": yesterday,
        "current": primary,
        "previous": previous,
        "days": daily,
    }


def calculate_deck_state(
    note_ids: Iterable[object], cards: Iterable[object], deck_stats: object, deck: str
) -> dict[str, int]:
    """Calculate note/card state without retaining card or note content."""
    notes = {int(note_id) for note_id in note_ids}
    cards_by_note: dict[int, list[dict[str, int]]] = defaultdict(list)
    card_count = 0

    for raw in cards:
        if not isinstance(raw, dict):
            raise StatsDataError("AnkiConnect returned invalid cardsInfo data.")
        note_value = raw.get("note", raw.get("noteId"))
        queue_value = raw.get("queue")
        type_value = raw.get("type")
        interval_value = raw.get("interval", raw.get("ivl"))
        if None in {note_value, queue_value, type_value, interval_value}:
            raise StatsDataError("AnkiConnect card info is missing state fields.")
        note_id = int(note_value)
        notes.add(note_id)
        cards_by_note[note_id].append(
            {
                "queue": int(queue_value),
                "type": int(type_value),
                "interval": int(interval_value),
            }
        )
        card_count += 1

    introduced = 0
    mature = 0
    for note_id in notes:
        active = [card for card in cards_by_note.get(note_id, []) if card["queue"] != -1]
        if not active:
            continue
        if any(card["type"] != 0 for card in active):
            introduced += 1
        if all(card["type"] != 0 and card["interval"] >= 21 for card in active):
            mature += 1

    stats = _select_deck_stats(deck_stats, deck)
    return {
        "learning_items": len(notes),
        "introduced_items": introduced,
        "mature_items": mature,
        "cards": card_count,
        "due_new": _required_int(stats, "new_count"),
        "due_learning": _required_int(stats, "learn_count"),
        "due_review": _required_int(stats, "review_count"),
    }


def _localized_now(tz: ZoneInfo, now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(tz)
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    return now.astimezone(tz)


def _period(events: list[dict[str, Any]], dates: set[date]) -> dict[str, Any]:
    selected = [event for event in events if event["date"] in dates]
    first_answers: dict[tuple[int, date], dict[str, Any]] = {}
    for event in selected:
        first_answers.setdefault((event["card_id"], event["date"]), event)
    true_passes = sum(event["rating"] != 1 for event in first_answers.values())
    true_total = len(first_answers)
    answers = len(selected)
    passes = sum(event["rating"] != 1 for event in selected)
    return {
        "answers": answers,
        "unique_cards": len({event["card_id"] for event in selected}),
        "duration_ms": sum(event["duration_ms"] for event in selected),
        "again": sum(event["rating"] == 1 for event in selected),
        "answer_passes": passes,
        "answer_pass_rate": passes / answers if answers else None,
        "true_passes": true_passes,
        "true_total": true_total,
        "true_retention": true_passes / true_total if true_total else None,
    }


def _select_deck_stats(payload: object, deck: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise StatsDataError("AnkiConnect returned invalid getDeckStats data.")
    matches = [
        value
        for value in payload.values()
        if isinstance(value, dict) and value.get("name") == deck
    ]
    if len(matches) != 1:
        raise StatsDataError(f"AnkiConnect returned no unique deck stats for {deck}.")
    return matches[0]


def _required_int(payload: dict[str, Any], key: str) -> int:
    try:
        return int(payload[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise StatsDataError(f"Deck statistics are missing {key}.") from exc
