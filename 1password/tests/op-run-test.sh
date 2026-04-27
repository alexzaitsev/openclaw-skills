#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OP_RUN="$ROOT_DIR/bin/op-run"
TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/op-run-test.XXXXXX")"
MOCK_BIN="$TEST_TMP/bin"
mkdir -p "$MOCK_BIN"

cleanup() {
  rm -rf "$TEST_TMP"
}
trap cleanup EXIT

fail() {
  printf 'not ok - %s\n' "$1" >&2
  exit 1
}

assert_eq() {
  local expected="$1"
  local actual="$2"
  local message="$3"

  [[ "$actual" == "$expected" ]] || fail "$message: expected [$expected], got [$actual]"
}

assert_contains() {
  local needle="$1"
  local haystack="$2"
  local message="$3"

  [[ "$haystack" == *"$needle"* ]] || fail "$message: missing [$needle] in [$haystack]"
}

assert_not_contains() {
  local needle="$1"
  local haystack="$2"
  local message="$3"

  [[ "$haystack" != *"$needle"* ]] || fail "$message: found [$needle] in [$haystack]"
}

run_case() {
  local name="$1"
  shift

  local stdout_file="$TEST_TMP/${name}.stdout"
  local stderr_file="$TEST_TMP/${name}.stderr"
  local status_file="$TEST_TMP/${name}.status"

  set +e
  PATH="$MOCK_BIN:$PATH" "$OP_RUN" "$@" >"$stdout_file" 2>"$stderr_file"
  local status=$?
  set -e

  printf '%s' "$status" > "$status_file"
}

cat > "$MOCK_BIN/op" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "$*" > "${MOCK_OP_ARGV_FILE:?}"
printf '%s\n' "${OPENCLAW_USERNAME:-}" > "${MOCK_OP_USERNAME_FILE:?}"
printf '%s\n' "${OPENCLAW_PASSWORD:-}" > "${MOCK_OP_PASSWORD_FILE:?}"

if [[ "${MOCK_OP_MODE:-success}" == "credential_error" ]]; then
  printf 'could not resolve secret reference for item abc123safeitem\n' >&2
  exit 1
fi

if [[ "$#" -lt 2 || "$1" != "run" || "$2" != "--" ]]; then
  printf 'unexpected op invocation\n' >&2
  exit 99
fi

shift 2
"$@"
MOCK
chmod +x "$MOCK_BIN/op"

export MOCK_OP_ARGV_FILE="$TEST_TMP/op.argv"
export MOCK_OP_USERNAME_FILE="$TEST_TMP/op.username"
export MOCK_OP_PASSWORD_FILE="$TEST_TMP/op.password"

test_success_passes_fixed_references_and_argv() {
  export MOCK_OP_MODE="success"

  run_case "success" --item-uuid "abc123safeitem" -- bash -c 'printf "child-ok\n"'

  assert_eq "0" "$(cat "$TEST_TMP/success.status")" "success status"
  assert_eq "child-ok" "$(tr -d '\n' < "$TEST_TMP/success.stdout")" "success stdout"
  assert_eq "run -- bash -c printf \"child-ok\\n\"" "$(cat "$MOCK_OP_ARGV_FILE")" "op argv"
  assert_eq "op://OpenClaw/abc123safeitem/username" "$(cat "$MOCK_OP_USERNAME_FILE")" "username reference"
  assert_eq "op://OpenClaw/abc123safeitem/password" "$(cat "$MOCK_OP_PASSWORD_FILE")" "password reference"
}

test_child_failure_preserves_status_and_output() {
  export MOCK_OP_MODE="success"

  run_case "child_fail" --item-uuid "abc123safeitem" -- bash -c 'printf "CHILD_FAILURE\n" >&2; exit 7'

  assert_eq "7" "$(cat "$TEST_TMP/child_fail.status")" "child failure status"
  assert_contains "CHILD_FAILURE" "$(cat "$TEST_TMP/child_fail.stderr")" "child stderr"
}

test_credential_failure_is_redacted() {
  export MOCK_OP_MODE="credential_error"

  run_case "credential_fail" --item-uuid "abc123safeitem" -- bash -c 'printf "unreachable\n"'

  assert_eq "1" "$(cat "$TEST_TMP/credential_fail.status")" "credential failure status"
  assert_eq "" "$(cat "$TEST_TMP/credential_fail.stdout")" "credential failure stdout"
  assert_eq "ERR_CREDENTIAL_UNAVAILABLE" "$(tr -d '\n' < "$TEST_TMP/credential_fail.stderr")" "credential failure stderr"
  assert_not_contains "abc123safeitem" "$(cat "$TEST_TMP/credential_fail.stderr")" "credential failure must not echo uuid"
  assert_not_contains "op://" "$(cat "$TEST_TMP/credential_fail.stderr")" "credential failure must not echo reference"
}

test_invalid_usage_is_generic() {
  local cases=(
    "missing_all"
    "missing_separator"
    "missing_child"
    "unknown_option"
    "unsafe_uuid"
  )

  run_case "missing_all"
  run_case "missing_separator" --item-uuid "abc123safeitem" bash -c true
  run_case "missing_child" --item-uuid "abc123safeitem" --
  run_case "unknown_option" --title "Example" -- bash -c true
  run_case "unsafe_uuid" --item-uuid "op://OpenClaw/item/password" -- bash -c true

  for name in "${cases[@]}"; do
    assert_eq "64" "$(cat "$TEST_TMP/${name}.status")" "$name status"
    assert_eq "ERR_USAGE" "$(tr -d '\n' < "$TEST_TMP/${name}.stderr")" "$name stderr"
  done
}

test_op_run_avoids_forbidden_cli_patterns() {
  local op_run_text
  op_run_text="$(grep -Ev '^\s*#' "$OP_RUN")"

  ! grep -Eq '(^|[[:space:]])op[[:space:]]+(read|inject|signin|account|item|vault)[[:space:]]' <<< "$op_run_text" \
    || fail "op-run must not use unsupported op subcommands"
  ! grep -Eq '(^|[[:space:]])(tmux|capture-pane|printenv|env|set -x|tee)([[:space:]]|$)' <<< "$op_run_text" \
    || fail "op-run contains forbidden secret-handling helper"
  ! grep -Eq -- '--no-masking' <<< "$op_run_text" \
    || fail "op-run must not disable masking"
  # shellcheck disable=SC2016
  ! grep -Eq '(^|[[:space:]])eval([[:space:]]|$)|`[^`]+`' <<< "$op_run_text" \
    || fail "op-run must not use command evaluation"
}

test_success_passes_fixed_references_and_argv
test_child_failure_preserves_status_and_output
test_credential_failure_is_redacted
test_invalid_usage_is_generic
test_op_run_avoids_forbidden_cli_patterns

printf 'ok - op-run tests passed\n'
