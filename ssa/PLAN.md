# `ssa` design record

## Goal

Wrap OpenSSH so an interactive shell, tmux attachment, or forwarding-only session reconnects after credential expiry, VPN loss, captive portals, timeouts, network changes, and remote reboots. Preserve OpenSSH's terminal behavior and configuration instead of replacing either.

## Invariants

- **No blocking prompts:** supervised sessions and probes force `BatchMode=yes`; recovery waits for external state to change.
- **No implicit command replay:** a supplied remote command that returns 255 may already have run because remote stderr and OpenSSH diagnostics share one stream. Retry only with `--retry-command`.
- **Finite, side-effect-light probes:** connection probes bypass multiplexing, retain routing/authentication options, clear forwards, and remove session-only flags such as `-N`; they must execute `true` and return.
- **Detect dead sessions:** refuse effective SSH configuration with `ServerAliveInterval=0` rather than silently rewriting it.
- **Fail closed on trust changes:** never repair `known_hosts`; stop on a changed or unverifiable host key.
- **Own child lifecycle:** `INT`/`TERM` stop both OpenSSH and the stderr copier and return conventional 128+signal statuses.
- **Readable long waits:** probe cadence and status-print cadence remain independent.

## Why Bash

Bash is the minimal fit because OpenSSH can retain the terminal directly while the wrapper supplies only process supervision, stderr classification, and backoff. Python would need terminal/signal plumbing plus an interpreter; fish makes script and signal portability harder; Lean does not model the operating-system and network boundary this behavior depends on.

## Compound-engineering gate

`./test-ssa` replaces OpenSSH, certificate inspection, and the captive-portal HTTP check with local stubs. Every discovered failure becomes a regression plan; the suite must remain offline, bounded, and green alongside `bash -n ssa test-ssa` and `shellcheck ssa test-ssa`.
