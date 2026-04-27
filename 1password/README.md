# 1Password OpenClaw Skill

Hardened local OpenClaw skill for running approved child commands with credentials from a known 1Password Login item, without returning raw secrets to the model.

This repository contains the skill implementation only. It does not install the 1Password CLI, create the service account, configure OpenClaw agents, or deploy files onto a VM.

## Purpose

V1 supports one narrow pattern:

```bash
bin/op-run --item-uuid <1password-login-item-uuid> -- <command> [args...]
```

`op-run` builds fixed 1Password references for the `OpenClaw` vault:

```text
OPENCLAW_USERNAME=op://OpenClaw/<item-uuid>/username
OPENCLAW_PASSWORD=op://OpenClaw/<item-uuid>/password
```

It then invokes the child command through:

```bash
op run -- <command> [args...]
```

The child command receives `OPENCLAW_USERNAME` and `OPENCLAW_PASSWORD` in its environment. The raw credential values should not appear in model-visible output, command-line arguments, logs, transcripts, or files.

## Repository Layout

- `SKILL.md` defines the OpenClaw skill contract, dependencies, allowed V1 behavior, and safety boundaries.
- `bin/op-run` is the executable wrapper that validates arguments and invokes `op run`.
- `tests/op-run-test.sh` is a mock-based test suite for the wrapper.
- `agents/openai.yaml` contains UI metadata and disables implicit invocation.

## Requirements

Runtime requirements:

- Official 1Password CLI binary: `op`
- `OP_SERVICE_ACCOUNT_TOKEN` present in the runtime environment
- A dedicated 1Password vault named `OpenClaw`
- Login items using standard `username` and `password` fields

Development verification requirements:

- Bash
- ShellCheck

## Safety Model

V1 intentionally does not support:

- `op read`
- `op inject`
- item or vault discovery
- item-title lookup
- caller-defined environment variable names
- arbitrary 1Password secret references
- desktop-app integration
- interactive `op signin`

Invalid or unauthorized item requests should fail with:

```text
ERR_CREDENTIAL_UNAVAILABLE
```

The error must not include UUIDs, item titles, vault details, raw 1Password CLI errors, secret references, or token values.

## Tests

Run the full local verification:

```bash
tests/op-run-test.sh
shellcheck bin/op-run tests/op-run-test.sh
bash -n bin/op-run tests/op-run-test.sh
git diff --check
```

The tests use a fake `op` binary. They do not contact 1Password and do not require real credentials.

## Deployment Note

For an OpenClaw workspace deployment, copy the runtime skill files into the local skill path, typically:

```text
/home/claw/.openclaw/workspace/skills/1password/
```

The service-account token must stay outside this repository and outside the workspace Git history.
