#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
PORT=18765
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
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(sys.argv[1])
ACTIONS_LOG = Path(sys.argv[2])
FAIL_SYNC = ACTIONS_LOG.with_suffix(".fail-sync")


class Handler(BaseHTTPRequestHandler):
    deck_names = {"adjetivos", "Default", "English", "Español", "Vacía", "verbos"}
    card_decks = {301: "Default", 302: "Default"}
    card_notes = {101: 7001, 102: 7002, 201: 7003}
    note_cards = {}
    next_note_id = 123456789
    next_card_id = 301
    known_notes = {
        7001: {
            "fields": {
                "Front": {"value": "decir"},
                "Back": {"value": "говорить; сказать"},
            },
            "tags": ["source:old", "review-later"],
        },
        7002: {
            "fields": {
                "Front": {"value": "con imagen<br><img src=\"test.png\">"},
                "Back": {"value": "with image"},
            },
            "tags": [],
        },
        7003: {
            "fields": {
                "Front": {"value": "yo digo"},
                "Back": {"value": "я говорю"},
            },
            "tags": [],
        }
    }

    def log_message(self, _format, *_args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        action = payload["action"]
        params = payload.get("params", {})
        response = {"result": None, "error": None}
        with ACTIONS_LOG.open("a", encoding="utf-8") as log:
            log.write(f"{action}\n")

        if action == "version":
            response["result"] = 6
        elif action == "deckNames":
            response["result"] = sorted(type(self).deck_names)
        elif action == "modelNames":
            response["result"] = ["Basic", "Basic (type in the answer + reverse)"]
        elif action == "modelFieldNames":
            response["result"] = ["Front", "Back", "Context", "Example"]
        elif action == "canAddNotes":
            for note in params["notes"]:
                fields = note["fields"]
                if fields["Front"] == "alto" and fields["Context"] == "opposite of bajo" and fields != {
                    "Front": "alto",
                    "Back": "tall",
                    "Context": "opposite of bajo",
                    "Example": "El edificio es alto.",
                }:
                    response["error"] = "single-note fields were mapped incorrectly"
                if fields["Front"] == "alto" and "deck:general" not in note["tags"]:
                    response["error"] = "single note is missing its deck role tag"
                if fields["Front"] == "¿Puedes cambiar tus planes?" and fields != {
                    "Front": "¿Puedes cambiar tus planes?",
                    "Back": "Ты можешь изменить свои планы?",
                    "Context": "вежливый вопрос",
                    "Example": "Puedes cambiar los planes.",
                }:
                    response["error"] = "batch-note fields were mapped incorrectly"
                if fields["Front"] == "¿Puedes cambiar tus planes?" and "deck:general" not in note["tags"]:
                    response["error"] = "general batch note is missing its deck role tag"
                if fields["Front"] == "cambiar" and "deck:verbos" not in note["tags"]:
                    response["error"] = "verbos batch note is missing its deck role tag"
                if fields["Front"] == "la carne" and "deck:general" not in note["tags"]:
                    response["error"] = "imported note is missing its deck role tag"
            response["result"] = [True for _ in params["notes"]]
        elif action == "addNote":
            note_id = type(self).next_note_id
            card_ids = [type(self).next_card_id, type(self).next_card_id + 1]
            type(self).next_note_id += 1
            type(self).next_card_id += 2
            type(self).note_cards[note_id] = card_ids
            for card_id in card_ids:
                type(self).card_decks[card_id] = "Default"
            response["result"] = note_id
        elif action == "findNotes":
            query = params["query"]
            if "yo digo" in query:
                response["result"] = [7003]
            elif "decir" in query:
                response["result"] = [7001]
            else:
                response["result"] = []
        elif action == "notesInfo":
            response["result"] = [
                {
                    **self.known_notes[note_id],
                    "tags": [
                        unicodedata.normalize("NFD", tag)
                        for tag in self.known_notes[note_id]["tags"]
                    ],
                }
                for note_id in params["notes"]
                if note_id in self.known_notes
            ]
        elif action == "updateNoteFields":
            note = params["note"]
            note_id = note["id"]
            if note_id not in self.known_notes:
                response["error"] = f"unknown note: {note_id}"
            else:
                fields = self.known_notes[note_id]["fields"]
                for name, value in note["fields"].items():
                    fields[name] = {"value": value}
                response["result"] = None
        elif action in {"addTags", "removeTags"}:
            for note_id in params["notes"]:
                note = self.known_notes.get(note_id)
                if note is None:
                    response["error"] = f"unknown note: {note_id}"
                    break
                requested_tags = params["tags"].split()
                if action == "addTags":
                    for tag in requested_tags:
                        if tag not in note["tags"]:
                            note["tags"].append(tag)
                    # AnkiConnect may normalize tag order when it returns a
                    # note. This makes the mock cover order-independent
                    # post-write verification.
                    note["tags"].sort(key=str.casefold)
                else:
                    note["tags"] = [tag for tag in note["tags"] if tag not in requested_tags]
            response["result"] = None
        elif action == "sync":
            if FAIL_SYNC.exists():
                response["error"] = "mock sync failure"
            else:
                response["result"] = None
        elif action == "findCards":
            query = params["query"]
            if query.startswith("nid:"):
                response["result"] = self.note_cards.get(int(query[4:]), [])
            elif "Vacía" in query:
                response["result"] = []
            elif "adjetivos" in query:
                response["result"] = [101, 102]
            else:
                response["result"] = [201]
        elif action == "cardsInfo":
            response["result"] = [
                {
                    "cardId": card,
                    "note": self.card_notes.get(card, card + 1000),
                    "deckName": self.card_decks.get(card, "Español"),
                }
                for card in params["cards"]
            ]
        elif action == "changeDeck":
            for card in params["cards"]:
                self.card_decks[card] = params["deck"]
            response["result"] = None
        elif action == "createDeck":
            type(self).deck_names.add(params["deck"])
            response["result"] = None
        elif action == "deleteDecks":
            decks = params["decks"]
            if not params.get("cardsToo"):
                response["error"] = "deck deletion requires cardsToo=true"
            else:
                for deck in decks:
                    type(self).deck_names.discard(deck)
            response["result"] = None
        elif action == "storeMediaFile":
            response["result"] = params.get("filename")
        else:
            response["error"] = f"unsupported action: {action}"

        data = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
PY
SERVER_PID=$!
sleep 0.5
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  cat "$TMP_DIR/server.log" >&2
  exit 1
fi

export ANKI_CONNECT_URL="http://127.0.0.1:$PORT"

python3 - "$ROOT/bin/anki-tool" <<'PY'
import runpy
import sys

tool = runpy.run_path(sys.argv[1])
assert tool["html_back"]("ответ", "пояснение") == (
    'ответ<br><div class="context">Контекст: пояснение</div>'
)
assert tool["split_back"](
    'ответ<br><div class="context">Контекст: пояснение</div>'
) == ("ответ", "пояснение")
PY

"$ROOT/bin/anki-tool" ping > "$TMP_DIR/ping.txt"
grep -F "AnkiConnect API version: 6" "$TMP_DIR/ping.txt" >/dev/null

"$ROOT/bin/anki-tool" decks > "$TMP_DIR/decks.txt"
grep -F "Español" "$TMP_DIR/decks.txt" >/dev/null

"$ROOT/bin/anki-tool" deck-info --deck Español > "$TMP_DIR/deck-info.txt"
grep -F "DECK INFO" "$TMP_DIR/deck-info.txt" >/dev/null
grep -F "deck: Español" "$TMP_DIR/deck-info.txt" >/dev/null
grep -F "cards: 1" "$TMP_DIR/deck-info.txt" >/dev/null
grep -F "notes: 1" "$TMP_DIR/deck-info.txt" >/dev/null
grep -F "child_decks: 0" "$TMP_DIR/deck-info.txt" >/dev/null
grep -F "empty: no" "$TMP_DIR/deck-info.txt" >/dev/null

"$ROOT/bin/anki-tool" create-deck --deck Italiano > "$TMP_DIR/create-deck-dry.txt"
grep -F "DRY RUN create-deck" "$TMP_DIR/create-deck-dry.txt" >/dev/null
grep -F "deck: Italiano" "$TMP_DIR/create-deck-dry.txt" >/dev/null
CREATE_PLAN_ID="$(awk '/^plan_id:/ {print $2}' "$TMP_DIR/create-deck-dry.txt")"
[[ "$CREATE_PLAN_ID" =~ ^[0-9a-f]{16}$ ]]
"$ROOT/bin/anki-tool" create-deck --deck Italiano --execute --plan-id "$CREATE_PLAN_ID" \
  > "$TMP_DIR/create-deck-execute.txt"
grep -F "result: created deck Italiano" "$TMP_DIR/create-deck-execute.txt" >/dev/null
grep -F "sync: requested" "$TMP_DIR/create-deck-execute.txt" >/dev/null

"$ROOT/bin/anki-tool" delete-deck --deck Vacía > "$TMP_DIR/delete-empty-dry.txt"
grep -F "DRY RUN delete-deck" "$TMP_DIR/delete-empty-dry.txt" >/dev/null
grep -F "cards: 0" "$TMP_DIR/delete-empty-dry.txt" >/dev/null
grep -F "empty: yes" "$TMP_DIR/delete-empty-dry.txt" >/dev/null
grep -F "nonempty_confirmation_required: no" "$TMP_DIR/delete-empty-dry.txt" >/dev/null
EMPTY_DELETE_PLAN_ID="$(awk '/^plan_id:/ {print $2}' "$TMP_DIR/delete-empty-dry.txt")"
"$ROOT/bin/anki-tool" delete-deck --deck Vacía --execute --plan-id "$EMPTY_DELETE_PLAN_ID" \
  > "$TMP_DIR/delete-empty-execute.txt"
grep -F "result: deleted deck Vacía" "$TMP_DIR/delete-empty-execute.txt" >/dev/null
grep -F "sync: requested" "$TMP_DIR/delete-empty-execute.txt" >/dev/null

"$ROOT/bin/anki-tool" models > "$TMP_DIR/models.txt"
grep -F "Basic (type in the answer + reverse)" "$TMP_DIR/models.txt" >/dev/null

"$ROOT/bin/anki-tool" fields > "$TMP_DIR/fields.txt"
grep -F "[1] Front" "$TMP_DIR/fields.txt" >/dev/null
grep -F "[3] Context" "$TMP_DIR/fields.txt" >/dev/null
grep -F "[4] Example" "$TMP_DIR/fields.txt" >/dev/null

"$ROOT/bin/anki-tool" capabilities --json > "$TMP_DIR/capabilities.json"
grep -F '"version": 3' "$TMP_DIR/capabilities.json" >/dev/null
grep -F '"physical_deck": "language"' "$TMP_DIR/capabilities.json" >/dev/null
grep -F '"role_tag": "deck:<role>"' "$TMP_DIR/capabilities.json" >/dev/null
grep -F '"name": "create-deck"' "$TMP_DIR/capabilities.json" >/dev/null
grep -F '"name": "deck-info"' "$TMP_DIR/capabilities.json" >/dev/null
grep -F '"name": "delete-deck"' "$TMP_DIR/capabilities.json" >/dev/null
grep -F '"name": "edit-batch"' "$TMP_DIR/capabilities.json" >/dev/null
grep -F '"name": "tag-decks"' "$TMP_DIR/capabilities.json" >/dev/null
grep -F '"name": "stage-inbound-image"' "$TMP_DIR/capabilities.json" >/dev/null
grep -F '"Context"' "$TMP_DIR/capabilities.json" >/dev/null

"$ROOT/bin/anki-tool" check --deck Español --front decir > "$TMP_DIR/check-present.txt"
grep -F "CHECK" "$TMP_DIR/check-present.txt" >/dev/null
grep -F "matches: 1" "$TMP_DIR/check-present.txt" >/dev/null
grep -F "note_id=7001 decir -> говорить; сказать" "$TMP_DIR/check-present.txt" >/dev/null
grep -F "result: present" "$TMP_DIR/check-present.txt" >/dev/null

"$ROOT/bin/anki-tool" check --deck Español --front cambiar > "$TMP_DIR/check-absent.txt"
grep -F "matches: 0" "$TMP_DIR/check-absent.txt" >/dev/null
grep -F "result: absent" "$TMP_DIR/check-absent.txt" >/dev/null

"$ROOT/bin/anki-tool" search --deck Español --query "yo digo" > "$TMP_DIR/search.txt"
grep -F "SEARCH" "$TMP_DIR/search.txt" >/dev/null
grep -F "matches: 1" "$TMP_DIR/search.txt" >/dev/null
grep -F "note_id=7003 yo digo -> я говорю" "$TMP_DIR/search.txt" >/dev/null
grep -F "result: found" "$TMP_DIR/search.txt" >/dev/null

"$ROOT/bin/anki-tool" add-basic \
  --deck Español \
  --role general \
  --front "alto" \
  --back "tall" \
  --context "opposite of bajo" \
  --field Example "El edificio es alto." \
  --tag source:telegram \
  > "$TMP_DIR/add-dry.txt"
grep -F "DRY RUN add-basic" "$TMP_DIR/add-dry.txt" >/dev/null
grep -F "can_add: true" "$TMP_DIR/add-dry.txt" >/dev/null
grep -F "context: opposite of bajo" "$TMP_DIR/add-dry.txt" >/dev/null
grep -F "role: general" "$TMP_DIR/add-dry.txt" >/dev/null
grep -F "tags: source:telegram deck:general" "$TMP_DIR/add-dry.txt" >/dev/null
grep -F "field Example: El edificio es alto." "$TMP_DIR/add-dry.txt" >/dev/null

"$ROOT/bin/anki-tool" add-basic \
  --deck Español \
  --role números \
  --front "cero" \
  --back "ноль" \
  > "$TMP_DIR/unicode-role-dry.txt"
grep -F "role: números" "$TMP_DIR/unicode-role-dry.txt" >/dev/null
grep -F "tags: deck:números" "$TMP_DIR/unicode-role-dry.txt" >/dev/null

if "$ROOT/bin/anki-tool" add-basic \
  --deck Español \
  --role general \
  --front "campo desconocido" \
  --back "unknown field" \
  --field Unexpected "value" \
  > "$TMP_DIR/unknown-field.txt" 2>&1; then
  echo "expected add-basic to reject an unknown model field" >&2
  exit 1
fi
grep -F "Unknown model field(s): Unexpected" "$TMP_DIR/unknown-field.txt" >/dev/null

if "$ROOT/bin/anki-tool" add-basic \
  --deck Español \
  --role general \
  --front "etiqueta duplicada" \
  --back "duplicate tag" \
  --tag deck:verbos \
  > "$TMP_DIR/duplicate-role-tag.txt" 2>&1; then
  echo "expected add-basic to reject a manual deck:* tag" >&2
  exit 1
fi
grep -F "Do not pass deck:* with --tag" "$TMP_DIR/duplicate-role-tag.txt" >/dev/null

"$ROOT/bin/anki-tool" add-basic \
  --deck Español \
  --role general \
  --front "alto" \
  --back "tall" \
  --execute \
  > "$TMP_DIR/add-execute.txt"
grep -F "result: created note 123456789" "$TMP_DIR/add-execute.txt" >/dev/null
grep -F "cards: 301 302" "$TMP_DIR/add-execute.txt" >/dev/null
grep -F "verified_deck: Español" "$TMP_DIR/add-execute.txt" >/dev/null
grep -F "sync: requested" "$TMP_DIR/add-execute.txt" >/dev/null
[[ "$(grep -c '^sync$' "$TMP_DIR/actions.log")" -eq 3 ]]

"$ROOT/bin/anki-tool" move-note \
  --note-id 123456789 \
  --target English \
  > "$TMP_DIR/move-dry.txt"
grep -F "DRY RUN move-note" "$TMP_DIR/move-dry.txt" >/dev/null
grep -F "current_decks: Español" "$TMP_DIR/move-dry.txt" >/dev/null

"$ROOT/bin/anki-tool" move-note \
  --note-id 123456789 \
  --target English \
  --execute \
  > "$TMP_DIR/move-execute.txt"
grep -F "result: moved_cards=2" "$TMP_DIR/move-execute.txt" >/dev/null
grep -F "verified_deck: English" "$TMP_DIR/move-execute.txt" >/dev/null
grep -F "sync: requested" "$TMP_DIR/move-execute.txt" >/dev/null
[[ "$(grep -c '^sync$' "$TMP_DIR/actions.log")" -eq 4 ]]

"$ROOT/bin/anki-tool" sync > "$TMP_DIR/sync.txt"
grep -F "sync: requested" "$TMP_DIR/sync.txt" >/dev/null
[[ "$(grep -c '^sync$' "$TMP_DIR/actions.log")" -eq 5 ]]

touch "$TMP_DIR/actions.fail-sync"
if "$ROOT/bin/anki-tool" add-basic \
  --deck Español \
  --role general \
  --front "fallo" \
  --back "сбой" \
  --execute \
  > "$TMP_DIR/sync-failure.txt" 2>&1; then
  echo "expected automatic sync failure" >&2
  exit 1
fi
grep -F "succeeded locally, but automatic sync failed" \
  "$TMP_DIR/sync-failure.txt" >/dev/null
rm "$TMP_DIR/actions.fail-sync"

"$ROOT/bin/anki-tool" add-batch \
  --note Español general "¿Puedes cambiar tus planes?" \
    "Ты можешь изменить свои планы?" "вежливый вопрос" \
  --note Español verbos "cambiar" "менять; изменять" \
  --note-field 1 Example "Puedes cambiar los planes." \
  --tag source:telegram \
  > "$TMP_DIR/batch-dry.txt"
grep -F "DRY RUN add-batch" "$TMP_DIR/batch-dry.txt" >/dev/null
grep -F "notes: 2" "$TMP_DIR/batch-dry.txt" >/dev/null
grep -F "[1] OK Español [deck:general]: ¿Puedes cambiar tus planes?" \
  "$TMP_DIR/batch-dry.txt" >/dev/null
grep -F "[1] context: вежливый вопрос" "$TMP_DIR/batch-dry.txt" >/dev/null
grep -F "[1] tags: source:telegram deck:general" "$TMP_DIR/batch-dry.txt" >/dev/null
grep -F "[1] field Example: Puedes cambiar los planes." "$TMP_DIR/batch-dry.txt" >/dev/null
grep -F "[2] OK Español [deck:verbos]: cambiar" "$TMP_DIR/batch-dry.txt" >/dev/null
grep -F "[2] tags: source:telegram deck:verbos" "$TMP_DIR/batch-dry.txt" >/dev/null
[[ "$(grep -c '^sync$' "$TMP_DIR/actions.log")" -eq 6 ]]

"$ROOT/bin/anki-tool" add-batch \
  --note Español general "¿Puedes cambiar tus planes?" \
    "Ты можешь изменить свои планы?" "вежливый вопрос" \
  --note Español verbos "cambiar" "менять; изменять" \
  --note-field 1 Example "Puedes cambiar los planes." \
  --tag source:telegram \
  --execute \
  > "$TMP_DIR/batch-execute.txt"
grep -F "EXECUTE add-batch" "$TMP_DIR/batch-execute.txt" >/dev/null
[[ "$(grep -c 'verified_deck=Español' "$TMP_DIR/batch-execute.txt")" -eq 2 ]]
grep -F "result: created=2 skipped=0" "$TMP_DIR/batch-execute.txt" >/dev/null
grep -F "sync: requested" "$TMP_DIR/batch-execute.txt" >/dev/null
[[ "$(grep -c '^sync$' "$TMP_DIR/actions.log")" -eq 7 ]]

cat > "$TMP_DIR/cards.json" <<'JSON'
[
  {
    "deck": "Español",
    "role": "general",
    "cards": [
      {"spanish": "la carne", "russian": "meat"}
    ]
  }
]
JSON

"$ROOT/bin/anki-tool" import-json --source "$TMP_DIR/cards.json" > "$TMP_DIR/import.txt"
grep -F "DRY RUN import-json" "$TMP_DIR/import.txt" >/dev/null
grep -F "cards: 1" "$TMP_DIR/import.txt" >/dev/null
grep -F "[1] tags: deck:general" "$TMP_DIR/import.txt" >/dev/null

"$ROOT/bin/anki-tool" merge-decks \
  --source adjetivos \
  --source verbos \
  --target Español \
  --tag-original-deck \
  > "$TMP_DIR/merge.txt"
grep -F "DRY RUN merge-decks" "$TMP_DIR/merge.txt" >/dev/null
grep -F "source: adjetivos cards=2 notes=2" "$TMP_DIR/merge.txt" >/dev/null
grep -F "source: verbos cards=1 notes=1" "$TMP_DIR/merge.txt" >/dev/null

"$ROOT/bin/anki-tool" edit-note \
  --note-id 7001 \
  --context "англ. say" \
  --add-tag source:telegram \
  --add-tag grammar::verbs \
  --add-tag deck:números \
  --remove-tag review-later \
  > "$TMP_DIR/edit-dry.txt"
grep -F "DRY RUN edit-note" "$TMP_DIR/edit-dry.txt" >/dev/null
grep -F "current_context: <none>" "$TMP_DIR/edit-dry.txt" >/dev/null
grep -F "proposed_context: англ. say" "$TMP_DIR/edit-dry.txt" >/dev/null
grep -F "current_tags: source:old review-later" "$TMP_DIR/edit-dry.txt" >/dev/null
grep -F "add_tags: source:telegram grammar::verbs deck:números" "$TMP_DIR/edit-dry.txt" >/dev/null
grep -F "remove_tags: review-later" "$TMP_DIR/edit-dry.txt" >/dev/null
grep -F "proposed_tags: source:old source:telegram grammar::verbs deck:números" "$TMP_DIR/edit-dry.txt" >/dev/null
grep -F "result: dry run only" "$TMP_DIR/edit-dry.txt" >/dev/null

"$ROOT/bin/anki-tool" edit-note \
  --note-id 7001 \
  --front "decir (hablar)" \
  --back "говорить; сказать" \
  --context "англ. say" \
  --add-tag source:telegram \
  --add-tag grammar::verbs \
  --add-tag deck:números \
  --remove-tag review-later \
  --execute \
  > "$TMP_DIR/edit-execute.txt"
grep -F "result: updated note 7001" "$TMP_DIR/edit-execute.txt" >/dev/null
grep -F "verified_front: decir (hablar)" "$TMP_DIR/edit-execute.txt" >/dev/null
grep -F "verified_back: говорить; сказать" "$TMP_DIR/edit-execute.txt" >/dev/null
grep -F "verified_context: англ. say" "$TMP_DIR/edit-execute.txt" >/dev/null
grep -F "verified_tags: deck:números grammar::verbs source:old source:telegram" "$TMP_DIR/edit-execute.txt" >/dev/null
grep -F "sync: requested" "$TMP_DIR/edit-execute.txt" >/dev/null

"$ROOT/bin/anki-tool" edit-batch \
  --note 7001 "=" "англ. hablar" \
  --note 7003 "я говорю (speak)" "англ. speak" \
  --add-tag review-later \
  --remove-tag source:old \
  --note-add-tag 7003 source:telegram \
  --note-add-tag 7003 grammar::verbs \
  > "$TMP_DIR/edit-batch-dry.txt"
grep -F "DRY RUN edit-batch" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
grep -F "notes: 2" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
grep -F "[1] front: decir (hablar)" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
grep -F "[1] proposed_context: англ. hablar" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
grep -F "[2] front: yo digo" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
grep -F "[2] proposed_back: я говорю (speak)" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
grep -F "[1] current_tags: deck:números grammar::verbs source:old source:telegram" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
grep -F "[1] add_tags: review-later" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
grep -F "[1] remove_tags: source:old" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
grep -F "[1] proposed_tags: deck:números grammar::verbs source:telegram review-later" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
grep -F "[2] proposed_tags: review-later source:telegram grammar::verbs" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
grep -F "result: dry run only" "$TMP_DIR/edit-batch-dry.txt" >/dev/null
PLAN_ID="$(awk '/^plan_id:/ {print $2}' "$TMP_DIR/edit-batch-dry.txt")"
[[ "$PLAN_ID" =~ ^[0-9a-f]{16}$ ]]

"$ROOT/bin/anki-tool" edit-note --note-id 7001 --add-tag changed-after-plan --execute \
  > "$TMP_DIR/edit-batch-drift.txt"
if "$ROOT/bin/anki-tool" edit-batch \
  --note 7001 "=" "англ. hablar" \
  --note 7003 "я говорю (speak)" "англ. speak" \
  --add-tag review-later \
  --remove-tag source:old \
  --note-add-tag 7003 source:telegram \
  --note-add-tag 7003 grammar::verbs \
  --execute --plan-id "$PLAN_ID" \
  > "$TMP_DIR/edit-batch-stale.txt" 2>&1; then
  echo "expected edit-batch to reject stale plan" >&2
  exit 1
fi
grep -F "Batch plan is stale" "$TMP_DIR/edit-batch-stale.txt" >/dev/null

"$ROOT/bin/anki-tool" edit-batch \
  --note 7001 "=" "англ. hablar" \
  --note 7003 "я говорю (speak)" "англ. speak" \
  --add-tag review-later \
  --remove-tag source:old \
  --note-add-tag 7003 source:telegram \
  --note-add-tag 7003 grammar::verbs \
  > "$TMP_DIR/edit-batch-fresh-dry.txt"
FRESH_PLAN_ID="$(awk '/^plan_id:/ {print $2}' "$TMP_DIR/edit-batch-fresh-dry.txt")"

"$ROOT/bin/anki-tool" edit-batch \
  --note 7001 "=" "англ. hablar" \
  --note 7003 "я говорю (speak)" "англ. speak" \
  --add-tag review-later \
  --remove-tag source:old \
  --note-add-tag 7003 source:telegram \
  --note-add-tag 7003 grammar::verbs \
  --execute --plan-id "$FRESH_PLAN_ID" \
  > "$TMP_DIR/edit-batch-execute.txt"
grep -F "EXECUTE edit-batch" "$TMP_DIR/edit-batch-execute.txt" >/dev/null
grep -F "updated_note=7001 front=decir (hablar)" "$TMP_DIR/edit-batch-execute.txt" >/dev/null
grep -F "updated_note=7003 front=yo digo" "$TMP_DIR/edit-batch-execute.txt" >/dev/null
grep -F "result: updated=2" "$TMP_DIR/edit-batch-execute.txt" >/dev/null
grep -F "tags=changed-after-plan deck:números grammar::verbs review-later source:telegram" "$TMP_DIR/edit-batch-execute.txt" >/dev/null
grep -F "tags=grammar::verbs review-later source:telegram" "$TMP_DIR/edit-batch-execute.txt" >/dev/null
grep -F "sync: requested" "$TMP_DIR/edit-batch-execute.txt" >/dev/null

if "$ROOT/bin/anki-tool" edit-note \
  --note-id 7002 \
  --front "con imagen nueva" \
  > "$TMP_DIR/edit-media.txt" 2>&1; then
  echo "expected edit-note to reject a field with media" >&2
  exit 1
fi
grep -F "has media in Front" "$TMP_DIR/edit-media.txt" >/dev/null

"$ROOT/bin/anki-tool" tag-decks --deck adjetivos --deck verbos \
  > "$TMP_DIR/tag-decks-dry.txt"
grep -F "DRY RUN tag-decks" "$TMP_DIR/tag-decks-dry.txt" >/dev/null
grep -F "deck: adjetivos tag: deck:adjetivos cards: 2 notes: 2 add_tag: 2 already_tagged: 0" \
  "$TMP_DIR/tag-decks-dry.txt" >/dev/null
grep -F "deck: verbos tag: deck:verbos cards: 1 notes: 1 add_tag: 1 already_tagged: 0" \
  "$TMP_DIR/tag-decks-dry.txt" >/dev/null
grep -F "total_add_tag: 3" "$TMP_DIR/tag-decks-dry.txt" >/dev/null
TAG_PLAN_ID="$(awk '/^plan_id:/ {print $2}' "$TMP_DIR/tag-decks-dry.txt")"
[[ "$TAG_PLAN_ID" =~ ^[0-9a-f]{16}$ ]]

"$ROOT/bin/anki-tool" tag-decks --deck adjetivos --deck verbos \
  --execute --plan-id "$TAG_PLAN_ID" > "$TMP_DIR/tag-decks-execute.txt"
grep -F "EXECUTE tag-decks" "$TMP_DIR/tag-decks-execute.txt" >/dev/null
grep -F "result: tagged_notes=3" "$TMP_DIR/tag-decks-execute.txt" >/dev/null
grep -F "sync: requested" "$TMP_DIR/tag-decks-execute.txt" >/dev/null

"$ROOT/bin/anki-tool" tag-decks --deck adjetivos --deck verbos \
  > "$TMP_DIR/tag-decks-repeat.txt"
grep -F "total_add_tag: 0" "$TMP_DIR/tag-decks-repeat.txt" >/dev/null

"$ROOT/bin/anki-tool" delete-deck --deck Español > "$TMP_DIR/delete-nonempty-dry.txt"
grep -F "DRY RUN delete-deck" "$TMP_DIR/delete-nonempty-dry.txt" >/dev/null
grep -F "cards: 1" "$TMP_DIR/delete-nonempty-dry.txt" >/dev/null
grep -F "notes: 1" "$TMP_DIR/delete-nonempty-dry.txt" >/dev/null
grep -F "empty: no" "$TMP_DIR/delete-nonempty-dry.txt" >/dev/null
grep -F "nonempty_confirmation_required: yes" "$TMP_DIR/delete-nonempty-dry.txt" >/dev/null
NONEMPTY_DELETE_PLAN_ID="$(awk '/^plan_id:/ {print $2}' "$TMP_DIR/delete-nonempty-dry.txt")"
if "$ROOT/bin/anki-tool" delete-deck --deck Español --execute \
  --plan-id "$NONEMPTY_DELETE_PLAN_ID" > "$TMP_DIR/delete-nonempty-unconfirmed.txt" 2>&1; then
  echo "expected delete-deck to require explicit non-empty confirmation" >&2
  exit 1
fi
grep -F -- "--confirm-nonempty" "$TMP_DIR/delete-nonempty-unconfirmed.txt" >/dev/null
"$ROOT/bin/anki-tool" delete-deck --deck Español --execute \
  --plan-id "$NONEMPTY_DELETE_PLAN_ID" --confirm-nonempty \
  > "$TMP_DIR/delete-nonempty-execute.txt"
grep -F "result: deleted deck Español" "$TMP_DIR/delete-nonempty-execute.txt" >/dev/null
grep -F "deleted_cards: 1" "$TMP_DIR/delete-nonempty-execute.txt" >/dev/null
grep -F "sync: requested" "$TMP_DIR/delete-nonempty-execute.txt" >/dev/null
if "$ROOT/bin/anki-tool" deck-info --deck Español > "$TMP_DIR/deleted-deck-info.txt" 2>&1; then
  echo "expected deleted deck to be absent" >&2
  exit 1
fi
grep -F "Missing deck(s): Español" "$TMP_DIR/deleted-deck-info.txt" >/dev/null

python3 -m py_compile "$ROOT/bin/anki-tool" "$ROOT/lib/anki_connect.py"
rm -rf "$ROOT/bin/__pycache__" "$ROOT/lib/__pycache__"
bash -n "$ROOT/tests/anki-tool-test.sh"
