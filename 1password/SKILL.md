---
name: 1password
description: Run approved child commands through the 1Password CLI using a service account and fixed Login-item environment variables, without exposing raw secrets to the model.
bins: ["op"]
env: ["OP_SERVICE_ACCOUNT_TOKEN"]
primaryEnv: "OP_SERVICE_ACCOUNT_TOKEN"
---

# 1Password

Use this skill only for hardened, service-account-backed 1Password operations on the OpenClaw VM. V1 exists to run approved child processes with known Login-item credentials; it is not a general-purpose secret retrieval skill.

## Requirements

- The official 1Password CLI binary `op` must be available on `PATH`.
- `OP_SERVICE_ACCOUNT_TOKEN` must already be present in the runtime environment.
- The service account must be scoped to the dedicated `OpenClaw` vault.
- Login credentials must live in standard Login fields named `username` and `password`.
- Callers must identify Login items by stable item UUID only.

Do not use desktop-app integration, interactive sign-in, terminal capture, or human-account authentication flows on the VM.

## Supported V1 Operation

The only supported secret-consuming operation is `op-run` child-process execution:

```bash
bin/op-run --item-uuid <1password-login-item-uuid> -- <command> [args...]
```

`op-run` constructs these fixed secret references:

```text
OPENCLAW_USERNAME=op://OpenClaw/<item-uuid>/username
OPENCLAW_PASSWORD=op://OpenClaw/<item-uuid>/password
```

It then invokes:

```bash
op run -- <command> [args...]
```

The child process receives `OPENCLAW_USERNAME` and `OPENCLAW_PASSWORD`. The child process must not need the item UUID.

## Hard Boundaries

- Do not retrieve raw secret values into chat, transcripts, logs, shell history, or long-lived files.
- Do not implement `op read` in V1.
- Do not implement `op inject` in V1.
- Do not implement broad discovery commands such as item or vault listing.
- Do not support item-title lookup.
- Do not support caller-defined environment variable names.
- Do not support arbitrary 1Password secret references.
- Do not pass secrets as command-line arguments.
- Do not disable 1Password CLI masking.
- Do not write secret-bearing temporary files.
- Do not use shell tracing around secret-bearing commands.

All execution must remain limited to a dedicated trusted OpenClaw path with explicit operator approval for every command. The main general-purpose agent should not expose this skill by default.

## Failure Behavior

Invalid `op-run` usage exits nonzero with a generic usage error.

If 1Password cannot resolve the requested Login item because it is missing, unauthorized, unavailable, or the service-account token is invalid, `op-run` prints only:

```text
ERR_CREDENTIAL_UNAVAILABLE
```

Do not echo item UUIDs, item titles, vault details, secret references, raw 1Password CLI errors, or token values in failure output.

If the child command starts and exits nonzero, preserve its exit status where practical. The child command remains responsible for keeping its own output non-secret.
