#!/usr/bin/env python3
"""Bounded AnkiConnect reads for the statistics executables."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from anki_connect import invoke
from stats_calculator import (
    StatsDataError,
    calculate_deck_state,
    calculate_history,
    history_start_id,
)
from stats_report import DECK_LABELS, render_report


CARD_CHUNK_SIZE = 500
DEFAULT_TIMEZONE = "America/Edmonton"


def collect_report(
    deck: str,
    timezone: str,
    *,
    sync_first: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    if deck not in DECK_LABELS:
        raise StatsDataError(f"Unsupported statistics deck: {deck}.")
    decks = invoke("deckNames")
    if not isinstance(decks, list) or deck not in decks:
        raise StatsDataError(f"Exact Anki deck is unavailable: {deck}.")
    if sync_first:
        invoke("sync")

    start_id = history_start_id(timezone, now)
    reviews = invoke("cardReviews", deck=deck, startID=start_id - 1)
    if not isinstance(reviews, list):
        raise StatsDataError("AnkiConnect returned invalid cardReviews data.")

    query = _quote_deck_query(deck)
    card_ids = invoke("findCards", query=query)
    note_ids = invoke("findNotes", query=query)
    if not isinstance(card_ids, list) or not isinstance(note_ids, list):
        raise StatsDataError("AnkiConnect returned invalid deck search data.")
    cards: list[dict[str, Any]] = []
    for offset in range(0, len(card_ids), CARD_CHUNK_SIZE):
        chunk = [int(card_id) for card_id in card_ids[offset : offset + CARD_CHUNK_SIZE]]
        result = invoke("cardsInfo", cards=chunk)
        if not isinstance(result, list) or len(result) != len(chunk):
            raise StatsDataError("AnkiConnect returned invalid cardsInfo data.")
        cards.extend(result)

    deck_stats = invoke("getDeckStats", decks=[deck])
    history = calculate_history(reviews, timezone, now)
    state = calculate_deck_state(note_ids, cards, deck_stats, deck)
    return {
        "deck": deck,
        "history": history,
        "state": state,
        "text": render_report(deck, history, state),
    }


def now_from_environment() -> datetime | None:
    value = os.environ.get("ANKI_STATS_NOW", "").strip()
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise StatsDataError("ANKI_STATS_NOW must include a timezone offset.")
    return parsed


def _quote_deck_query(deck: str) -> str:
    escaped = deck.replace("\\", "\\\\").replace('"', '\\"')
    return f'deck:"{escaped}"'
