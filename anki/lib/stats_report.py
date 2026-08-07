#!/usr/bin/env python3
"""Deterministic Markdown rendering for Anki statistics."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any


DECK_LABELS = {
    "Español": ("🇪🇸", "Испанский"),
    "English": ("🇬🇧", "Английский"),
}
WEEKDAY_LABELS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
MONTH_LABELS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)
def render_report(deck: str, history: dict[str, Any], state: dict[str, int]) -> str:
    flag, label = DECK_LABELS[deck]
    report_date = date.fromisoformat(history["report_date"])
    run_date = report_date + timedelta(days=1)
    yesterday = history["yesterday"]
    yesterday_new = _count(yesterday["new_cards"], "новый", "новых", "новых")
    lines = [
        f"{flag} {label} · {deck}",
        "",
        f"Вчера · {_display_date(report_date)}",
        (
            f"{yesterday['review_cards']} к повторению · {yesterday_new} · "
            f"{format_duration(yesterday['duration_ms'])}"
        ),
        f"Отвечено: {yesterday['final_card_passes']} из {yesterday['unique_cards']}",
        "",
        f"Сегодня · {_display_date(run_date)}",
        (
            f"{state['unstarted_cards']} не начато · "
            f"{state['studying_cards']} в изучении · "
            f"{state['mature_cards']} {_mature_word(state['mature_cards'])}"
        ),
        f"{state['due_review']} к повторению · {state['due_new']} новых",
    ]
    return "\n".join(lines)


def render_compact_report(
    deck: str, history: dict[str, Any], state: dict[str, int]
) -> str:
    return render_report(deck, history, state)


def format_duration(milliseconds: int) -> str:
    seconds = max(0, round(milliseconds / 1000))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours} ч {minutes} мин"
    if minutes:
        return f"{minutes} мин {seconds} с"
    return f"{seconds} с"


def format_percent(value: float | None) -> str:
    return "—" if value is None else f"{round(value * 100)}%"


def _display_date(value: date) -> str:
    weekday = WEEKDAY_LABELS[value.weekday()].lower()
    return f"{weekday} {value.day} {MONTH_LABELS[value.month - 1]}"


def _count(value: int, one: str, few: str, many: str) -> str:
    remainder_100 = abs(value) % 100
    remainder_10 = remainder_100 % 10
    if 11 <= remainder_100 <= 14:
        word = many
    elif remainder_10 == 1:
        word = one
    elif 2 <= remainder_10 <= 4:
        word = few
    else:
        word = many
    return f"{value} {word}"


def _mature_word(value: int) -> str:
    """Return the compact maturity label used in the deck-state summary."""
    remainder_100 = abs(value) % 100
    return "закреплён" if remainder_100 % 10 == 1 and remainder_100 != 11 else "закреплено"
