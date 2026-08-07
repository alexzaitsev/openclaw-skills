#!/usr/bin/env python3
"""Unit tests for pure Anki statistics calculations and rendering."""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from stats_calculator import calculate_deck_state, calculate_history  # noqa: E402
from stats_report import _count, _display_date, format_duration, render_report  # noqa: E402


TZ = ZoneInfo("America/Edmonton")
NOW = datetime(2026, 7, 20, 12, 0, tzinfo=TZ)


def review(
    when: str, card: int, rating: int, duration: int, review_type: int = 1
) -> list[int]:
    timestamp = int(datetime.fromisoformat(when).replace(tzinfo=TZ).timestamp() * 1000)
    return [timestamp, card, 0, rating, 1, 1, 2500, duration, review_type]


class StatisticsTest(unittest.TestCase):
    def test_russian_formatting_is_deterministic_and_declined(self) -> None:
        self.assertEqual(_display_date(date(2026, 7, 19)), "вс 19 июля")
        self.assertEqual(format_duration(3_387_000), "56 мин 27 с")
        self.assertEqual(format_duration(3_600_000), "1 ч 0 мин")
        forms = ("ответ", "ответа", "ответов")
        self.assertEqual(_count(1, *forms), "1 ответ")
        self.assertEqual(_count(2, *forms), "2 ответа")
        self.assertEqual(_count(5, *forms), "5 ответов")
        self.assertEqual(_count(11, *forms), "11 ответов")
        self.assertEqual(_count(21, *forms), "21 ответ")
        self.assertEqual(_count(22, *forms), "22 ответа")

    def test_history_metrics_distinguish_answers_cards_and_first_attempts(self) -> None:
        rows = [
            review("2026-07-19T08:00:00", 1, 1, 1000),
            review("2026-07-19T08:05:00", 1, 3, 2000),
            review("2026-07-19T09:00:00", 2, 4, 3000),
            review("2026-07-19T10:00:00", 3, 0, 9000),
            review("2026-07-13T08:00:00", 4, 3, 4000),
            review("2026-07-12T08:00:00", 5, 1, 5000),
        ]
        result = calculate_history(rows, "America/Edmonton", NOW)
        yesterday = result["yesterday"]
        self.assertEqual(yesterday["answers"], 3)
        self.assertEqual(yesterday["unique_cards"], 2)
        self.assertEqual(yesterday["new_cards"], 0)
        self.assertEqual(yesterday["review_cards"], 2)
        self.assertEqual(yesterday["final_card_passes"], 2)
        self.assertEqual(yesterday["duration_ms"], 6000)
        self.assertEqual(yesterday["again"], 1)
        self.assertAlmostEqual(yesterday["answer_pass_rate"], 2 / 3)
        self.assertEqual(yesterday["true_passes"], 1)
        self.assertEqual(yesterday["true_total"], 2)
        self.assertEqual(result["current"]["answers"], 4)
        self.assertEqual(result["previous"]["answers"], 1)
        self.assertEqual(result["current"]["days_studied"], 2)

    def test_calendar_boundaries_use_requested_timezone(self) -> None:
        rows = [
            review("2026-07-19T00:00:00", 1, 3, 1000),
            review("2026-07-20T00:00:00", 2, 3, 1000),
        ]
        result = calculate_history(rows, "America/Edmonton", NOW)
        self.assertEqual(result["yesterday"]["answers"], 1)

    def test_spring_transition_still_uses_civil_dates(self) -> None:
        now = datetime(2026, 3, 9, 12, 0, tzinfo=TZ)
        rows = [
            review("2026-03-08T00:00:00", 1, 3, 1000),
            review("2026-03-09T00:00:00", 2, 3, 1000),
        ]
        result = calculate_history(rows, "America/Edmonton", now)
        self.assertEqual(result["report_date"], "2026-03-08")
        self.assertEqual(result["yesterday"]["answers"], 1)

    def test_deck_state_counts_cards(self) -> None:
        cards = [
            {"note": 1, "queue": 2, "type": 2, "interval": 30},
            {"note": 1, "queue": 2, "type": 2, "interval": 40},
            {"note": 2, "queue": 0, "type": 0, "interval": 0},
            {"note": 2, "queue": 0, "type": 0, "interval": 0},
            {"note": 3, "queue": -1, "type": 2, "interval": 90},
        ]
        stats = {
            "99": {
                "name": "Español",
                "new_count": 12,
                "learn_count": 4,
                "review_count": 63,
            }
        }
        state = calculate_deck_state([1, 2, 3], cards, stats, "Español")
        self.assertEqual(state["cards"], 5)
        self.assertEqual(state["unstarted_cards"], 1)
        self.assertEqual(state["studying_cards"], 2)
        self.assertEqual(state["mature_cards"], 2)
        self.assertEqual(state["due_review"], 63)

    def test_report_is_deterministic_and_contains_only_requested_metrics(self) -> None:
        history = calculate_history(
            [review("2026-07-19T08:00:00", 1, 3, 1000, review_type=0)],
            "America/Edmonton",
            NOW,
        )
        state = {
            "cards": 2,
            "unstarted_cards": 1,
            "studying_cards": 1,
            "mature_cards": 0,
            "due_new": 1,
            "due_learning": 0,
            "due_review": 2,
        }
        report = render_report("Español", history, state)
        self.assertEqual(
            report,
            "**🇪🇸 Испанский · Español**\n\n"
            "**Вчера · вс 19 июля**\n"
            "```\n"
            "Повторено:  0\n"
            "Новых:      1\n"
            "Время:      0 мин\n"
            "```\n\n"
            "**Сегодня · пн 20 июля**\n"
            "```\n"
            "Повторить:  2\n"
            "Новых:      1\n"
            "```\n\n"
            "**Прогресс**\n"
            "```\n"
            "Не начато:  50% (1)\n"
            "Изучается:  50% (1)\n"
            "Закреплено: 0% (0)\n"
            "Новых на:   1 день вперед\n"
            "```",
        )
        self.assertNotIn("||", report)
        self.assertNotIn("Последние 7 дней", report)
        self.assertNotIn("Запоминание", report)
        self.assertNotIn("Снова", report)


if __name__ == "__main__":
    unittest.main()
