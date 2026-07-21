#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
PORT=18766
SERVER_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

python3 - "$PORT" "$TMP_DIR/actions.log" > "$TMP_DIR/server.log" 2>&1 <<'PY' &
from __future__ import annotations

import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

PORT = int(sys.argv[1])
ACTIONS = Path(sys.argv[2])
TZ = ZoneInfo("America/Edmonton")


def review(when, card, rating, duration):
    timestamp = int(datetime.fromisoformat(when).replace(tzinfo=TZ).timestamp() * 1000)
    return [timestamp, card, 0, rating, 1, 1, 2500, duration, 1]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        action = payload["action"]
        params = payload.get("params", {})
        with ACTIONS.open("a", encoding="utf-8") as log:
            log.write(f"{action}\n")
        result = None
        error = None
        if action == "deckNames":
            result = ["Default", "English", "Español"]
        elif action == "sync":
            result = None
        elif action == "cardReviews":
            if params["deck"] == "Español":
                result = [
                    review("2026-07-19T08:00:00", 101, 1, 1000),
                    review("2026-07-19T08:05:00", 101, 3, 2000),
                    review("2026-07-19T09:00:00", 102, 4, 3000),
                    review("2026-07-13T09:00:00", 103, 3, 4000),
                    review("2026-07-12T09:00:00", 104, 1, 5000),
                ]
            else:
                result = []
        elif action == "findCards":
            result = [101, 102, 103, 104] if "Español" in params["query"] else [201]
        elif action == "findNotes":
            result = [1, 2] if "Español" in params["query"] else [3]
        elif action == "cardsInfo":
            details = {
                101: {"cardId": 101, "note": 1, "queue": 2, "type": 2, "interval": 30},
                102: {"cardId": 102, "note": 1, "queue": 2, "type": 2, "interval": 40},
                103: {"cardId": 103, "note": 2, "queue": 0, "type": 0, "interval": 0},
                104: {"cardId": 104, "note": 2, "queue": 0, "type": 0, "interval": 0},
                201: {"cardId": 201, "note": 3, "queue": 0, "type": 0, "interval": 0},
            }
            result = [details[card] for card in params["cards"]]
        elif action == "getDeckStats":
            name = params["decks"][0]
            result = {
                "99": {
                    "deck_id": 99,
                    "name": name,
                    "new_count": 12 if name == "Español" else 1,
                    "learn_count": 4 if name == "Español" else 0,
                    "review_count": 63 if name == "Español" else 2,
                    "total_in_deck": 4 if name == "Español" else 1,
                }
            }
        else:
            error = f"unsupported action: {action}"
        body = json.dumps({"result": result, "error": error}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
PY
SERVER_PID=$!
sleep 0.5
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  cat "$TMP_DIR/server.log" >&2
  exit 1
fi

export ANKI_CONNECT_URL="http://127.0.0.1:$PORT"
export ANKI_STATS_NOW="2026-07-20T12:00:00-06:00"
export ANKI_STATS_TIMEZONE="America/Edmonton"
export ANKI_STATS_RUNTIME_ROOT="$ROOT"
export OPENCLAW_BIN="$ROOT/tests/fake-openclaw.py"
export FAKE_OPENCLAW_STATE="$TMP_DIR/cron.json"
export PYTHONDONTWRITEBYTECODE=1

python3 "$ROOT/tests/stats-test.py"

"$ROOT/bin/anki-stats" settings --json > "$TMP_DIR/settings.json"
grep -F '"declaration_key": "anki-stats:espanol"' "$TMP_DIR/settings.json" >/dev/null
grep -F '"enabled": false' "$TMP_DIR/settings.json" >/dev/null

"$ROOT/bin/anki-stats" preview --deck Español > "$TMP_DIR/preview.txt"
grep -F "**🇪🇸 Испанский · Español**" "$TMP_DIR/preview.txt" >/dev/null
grep -F "3 ответа · 2 карточки · 6 с" "$TMP_DIR/preview.txt" >/dev/null
grep -F "**Запоминание 50%** (1/2)" "$TMP_DIR/preview.txt" >/dev/null
grep -F "2 учебных элемента · начато 1" "$TMP_DIR/preview.txt" >/dev/null
grep -F "1 элемент закреплён · 4 карточки" "$TMP_DIR/preview.txt" >/dev/null
grep -F "**Доступно сейчас:** новых 12 · изучаются 4 · к повторению 63" "$TMP_DIR/preview.txt" >/dev/null

"$ROOT/bin/anki-stats-worker" --deck Español > "$TMP_DIR/worker.txt"
grep -F "**🇪🇸 Испанский · Español**" "$TMP_DIR/worker.txt" >/dev/null
[[ "$(grep -c '^sync$' "$TMP_DIR/actions.log")" -eq 1 ]]

"$ROOT/bin/anki-stats" configure \
  --deck Español \
  --enable \
  --time 07:45 \
  --days mon,tue,wed,thu,fri,sat \
  > "$TMP_DIR/configure-dry.txt"
grep -F "proposed_cron: 45 7 * * 1,2,3,4,5,6" "$TMP_DIR/configure-dry.txt" >/dev/null
PLAN_ID="$(awk '/^plan_id:/ {print $2}' "$TMP_DIR/configure-dry.txt")"
[[ "$PLAN_ID" =~ ^[0-9a-f]{16}$ ]]
"$ROOT/bin/anki-stats" configure \
  --deck Español \
  --enable \
  --time 07:45 \
  --days mon,tue,wed,thu,fri,sat \
  --execute \
  --plan-id "$PLAN_ID" \
  > "$TMP_DIR/configure-execute.txt"
grep -F "result: updated and verified" "$TMP_DIR/configure-execute.txt" >/dev/null
grep -F "cron: 45 7 * * 1,2,3,4,5,6" "$TMP_DIR/configure-execute.txt" >/dev/null

"$ROOT/bin/anki-stats" configure --deck Español --timezone America/Toronto \
  > "$TMP_DIR/timezone-dry.txt"
TIMEZONE_PLAN_ID="$(awk '/^plan_id:/ {print $2}' "$TMP_DIR/timezone-dry.txt")"
"$ROOT/bin/anki-stats" configure --deck Español --timezone America/Toronto \
  --execute --plan-id "$TIMEZONE_PLAN_ID" > "$TMP_DIR/timezone-execute.txt"
grep -F "America/Toronto" "$TMP_DIR/timezone-execute.txt" >/dev/null
grep -F '"ANKI_STATS_TIMEZONE": "America/Toronto"' \
  "$FAKE_OPENCLAW_STATE" >/dev/null

"$ROOT/bin/anki-stats" configure --deck Español --time 07:00 \
  > "$TMP_DIR/stale-dry.txt"
STALE_ID="$(awk '/^plan_id:/ {print $2}' "$TMP_DIR/stale-dry.txt")"
"$OPENCLAW_BIN" cron edit spanish-id --cron "15 7 * * 1,2,3,4,5,6" \
  --tz America/Edmonton --exact \
  --command-env ANKI_STATS_TIMEZONE=America/Edmonton --enable >/dev/null
if "$ROOT/bin/anki-stats" configure --deck Español --time 07:00 \
  --execute --plan-id "$STALE_ID" > "$TMP_DIR/stale-execute.txt" 2>&1; then
  echo "expected stale statistics plan to fail" >&2
  exit 1
fi
grep -F "plan is stale" "$TMP_DIR/stale-execute.txt" >/dev/null

if "$ROOT/bin/anki-stats" configure --deck Español --time 24:00 \
  > "$TMP_DIR/invalid-time.txt" 2>&1; then
  echo "expected invalid statistics time to fail" >&2
  exit 1
fi
grep -F "between 00:00 and 23:59" "$TMP_DIR/invalid-time.txt" >/dev/null

if "$ROOT/bin/anki-stats" configure --deck Español --timezone Not/AZone \
  > "$TMP_DIR/invalid-timezone.txt" 2>&1; then
  echo "expected invalid statistics timezone to fail" >&2
  exit 1
fi
grep -F "Unknown IANA timezone" "$TMP_DIR/invalid-timezone.txt" >/dev/null

"$OPENCLAW_BIN" cron tamper spanish-id delivery.accountId wrong
if "$ROOT/bin/anki-stats" settings > "$TMP_DIR/tampered.txt" 2>&1; then
  echo "expected immutable delivery tampering to fail" >&2
  exit 1
fi
grep -F "delivery account" "$TMP_DIR/tampered.txt" >/dev/null

PYTHONPYCACHEPREFIX="$TMP_DIR/pycache" python3 -m py_compile \
  "$ROOT/bin/anki-stats" \
  "$ROOT/bin/anki-stats-worker" \
  "$ROOT/lib/stats_calculator.py" \
  "$ROOT/lib/stats_cron.py" \
  "$ROOT/lib/stats_report.py" \
  "$ROOT/lib/stats_runtime.py"
bash -n "$ROOT/tests/anki-stats-test.sh"
