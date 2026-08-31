# `ssa` design record

## Goal

Wrap OpenSSH so an interactive shell, tmux attachment, or forwarding-only session
reconnects after credential expiry, VPN loss, captive portals, timeouts, network
changes, and remote reboots. Preserve OpenSSH's terminal behaviour and
configuration instead of replacing either.

## The gate

The eleven properties T1–T11 are stated in `README.md`; that table is the index and
is not repeated here. This file holds the rule that keeps them true:

> **Every property names the checks in `test-ssa` that discharge it, and every
> check names the property it serves. A property with no check is a claim. A check
> with no property is a habit.**

That rule is itself two checks (`every stated property has a check`, `every
labelled check has a stated property`), which read the `T<n>` labels out of
`README.md` and out of the suite and compare the two sets. So the link cannot rot
by someone adding prose, or a check, and stopping there.

Nothing in the gate is a habit. `./test-ssa` runs `bash -n` and `shellcheck` on
itself and on `ssa` as its first two checks, and the repo's `.pre-commit-config.yaml`
runs the suite whenever `ssa/` changes and `shellcheck` on every shell file in the
repo. The suite stays offline and bounded: OpenSSH, certificate inspection and the
captive-portal HTTP check are local stubs, and T11 creates a pty rather than
borrowing the caller's terminal.

Prefer a check that reads **data or argv** over one that samples behaviour, because
that is the class a plausible-looking edit cannot slip past — which is exactly how
the regression that produced this file got in. Four already do: the failure table is
held to T9's column budget and T10's uniqueness by reading the table out of the
script, every row of it is driven end to end in one loop over that same data, and T1
is enforced by reading the probe's real argv against a fixed list of the options
that may appear in it.

## Superseded

Kept because each was a real belief that a check now contradicts. Deleting them
invites the same edit twice.

- **"A probe should bypass multiplexing, so a stale socket cannot fake a healthy
  host."** Half right, and the wrong half was load-bearing. `-o ControlPath=none`
  made the probe stricter than the session, so on a host reached through a
  `ProxyCommand` — `aws ssm start-session`, a Midway bastion — the probe demanded
  credentials the session did not need and `ssa` waited out an outage that was not
  happening. Staleness belongs to `stale_master`, which runs before the probe loop;
  fidelity belongs to the probe. Now T1, with the argv check that names
  `ControlPath` if it comes back and an ordering check on `stale_master`.
- **"Three `case` statements over the same stderr are fine, they are small."** They
  each carried their own copy of the pattern list, so a class and the sentence
  printed for it could disagree, and a new failure mode was three edits. One table.
  Now T10.
- **"A duration is minutes and seconds."** An overnight wait — the case the print
  cadence exists for — read `655m00s`. Now T9.
- **"The reason is a string; compare it to see whether it changed."** A reason
  worded with a duration is a different string on every probe, so the comparison
  reported a change every time and `SSA_NOTE_EVERY` throttled nothing: five lines
  in twelve seconds where T9 predicts two. The comparison is now against the reason
  with the ticking part removed. This is the kind of defect that reads as correct
  code — nothing looks wrong at the line — and it is why T9's count half needs a
  check of its own on the credential path, not only on a connect failure.
- **"A width check on a real run's output is enough."** It saw nothing while the
  give-up line reached 97 columns, because no fixture in the suite produced a long
  reason on that shape. Every shape is now rendered at its worst case from the
  budget arithmetic, which is a property of the grammar rather than of a fixture.
- **"If `ssh-keygen` says nothing, `date` will fail and we return no note."**
  `date -d ''` succeeds and returns midnight today, so an unreadable certificate was
  reported as `cert expired 19h55m ago` — a false reason in wording indistinguishable
  from the true one, sending you to `mwinit` for nothing. A missing certificate is
  not an answer, and now says so by returning nothing.
- **"A probe may as well carry the user's `-q` and `-E`."** Both silence or redirect
  the stream the diagnosis is read from, so the probe kept working and stopped being
  able to say why it failed.
- **"Any key stops the reconnect."** A dying full-screen program leaves escape
  bytes in the input queue; a mouse report was aborting the reconnect. The key is
  named. Now T11.
- **"An unrecognised reason may be capped at 64 characters."** That made `ssa`'s
  own status line wrap, which is the failure the separate print cadence exists to
  avoid. The cap is now derived from the line grammar and checked against it.
- **"A cert note explains any rejected credential."** `Too many authentication
  failures` is not a cert expiry, and saying it was sent you to `mwinit` for
  nothing. The note is attached to one row, not to a class. Now T10.
- **"`--max-wait=SECS` needs no validation."** Bash reads a non-numeric value as
  0, which here means *wait forever* — the opposite of asking for a bound.

## Why Bash

Bash is the minimal fit because OpenSSH can retain the terminal directly while the
wrapper supplies only process supervision, stderr classification, and backoff.
Python would need terminal and signal plumbing plus an interpreter; fish makes
script and signal portability harder; Lean does not model the operating-system and
network boundary these theorems are about — `test-ssa` is the proof assistant this
problem has. The full argument, with the bash 4.2 sharp edges that cost real bugs,
is in `README.md`.
