# `ssa` design record

## Goal

Wrap OpenSSH so an interactive shell or tmux attachment reconnects after credential
expiry, VPN loss, captive portals, timeouts, network changes, and remote reboots.
Preserve OpenSSH's terminal behaviour and configuration instead of replacing either
— and take a host, not a copy of ssh's command line: every connection setting
belongs in `ssh_config`, where the probe and the session both read it.

## The gate

The thirteen properties T1–T13 are stated in `README.md`; that table is the index
and is not repeated here. This file holds the rule that keeps them true:

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

T12 and T13 are the exception that has to sample behaviour: a bound is a claim about
the clock, so the only way to check it is to point `ssa` at something that will not
come back and watch what it does next. They assert that the loop kept running rather
than an exact duration, so a loaded machine does not read as a regression.

`ssa` has no runtime knobs, which would make those checks unwritable if the suite
could not vary a constant. It generates a copy of the script with one constant
rewritten, and the rewrite fails unless it matches exactly one line — otherwise a
renamed constant would leave the check green and testing nothing, which is the
same class of silent rot the data checks exist to prevent.

## Kept deliberately short

Not defects, and not worth the code they would take here:

- `stop` signals the `ssh` it started and its `tee`, not a `ProxyCommand`
  grandchild. Reaching one means a process group, and putting `ssh` in a new session
  is exactly what T11 depends on *not* doing. T13 covers the part that costs
  something — such a child cannot delay us — rather than the part that does not.
- The classifier is substring matching against a table, so `ssh -v` output remains
  something it reads by luck rather than by grammar. `TAIL_LINES` keeps luck from
  compounding; a real parser would mean the debug-output dependency this deliberately
  avoids.
- Refusing ssh's flags means a setting that has no `ssh_config` spelling cannot be
  passed at all. There is no such setting among the ones this is used with, and the
  refusal names the flag, so the failure is a sentence rather than a silent
  difference between the probe and the session.

## Superseded

Kept because each was a real belief that a check now contradicts. Deleting them
invites the same edit twice.

- **"A probe must be a filtered copy of the caller's argv."** That is what 42 lines
  of hand-rolled getopt were for: walking clusters, consuming argument-taking flags,
  deciding per flag whether a probe may keep it. Each decision could fail in either
  direction, and both directions are silent -- stricter and `ssa` waits out an
  outage that is not happening, laxer and it reconnects into an instant failure.
  ssh's flags are now refused, naming the flag and pointing at `ssh_config`, which
  both the probe and the session read; the probe's argv is fixed. T1 stopped being
  an argv-diff proof and became a sentence, and `-f`, `-q`, `-E`, `-N` and the rest
  need no cases of their own.
- **"Every timing knob wants an env var, and a wait wants a bound."** Nine knobs,
  of which one was ever passed. `--max-wait` was never used and gave up on a wait
  that only a person can judge -- a certificate about to be refreshed is indefinite,
  so the bound that means something is `^C`. Constants now, and the checks that need
  a different one generate a copy of the script with that line rewritten, which
  fails loudly unless it matches exactly one line. What must still terminate is each
  *call*, which is T12.
- **"`--max-wait` is checked often enough."** It was read *between* calls, and then
  a call was made that had no obligation to return: `-O check` has no bound of its
  own, and `ConnectTimeout` does not apply to a connection handed to a live master,
  so `--max-wait=1` exited after 3s and after 4s -- and in the worst case after that
  master's whole keepalive, five minutes on the SSM hosts. Every call now runs under
  `timeout`. Now T12, which outlived the flag that motivated it.
- **"ssh exiting means its stderr has reached us."** A `ProxyCommand` descendant
  inherits fd 2, so the fifo's write end outlives `ssh` and the `tee` reading it
  never sees EOF; waiting on it handed a grandchild the power to delay the
  diagnosis, and the deadline with it, for as long as it liked. `timeout` does not
  help -- it kills the process it started, not that child -- and a `$(...)` capture
  waits on the write end rather than on the process, so a probe had the same hole.
  Bounded drain for the session, a file rather than a pipe for the probe. Now T13.
- **"The whole of stderr is the right thing to search."** It is shared: the remote
  command writes to it, a host with `StrictHostKeyChecking` off warns on every
  connect, and `ssh -v` reports a refusal per address before connecting through
  another. So a drop was being classified from a line left by an attempt that
  recovered -- `connection refused`, down the connect path, refined with a portal
  guess. Only the last `TAIL_LINES` lines, which is the depth a real transcript
  needs. Row order still decides, because a proxy speaks before ssh does. Now T10.
- **"A 403 from the SSM proxy is a handshake refusal."** It is the generic line
  `ssh` prints underneath the proxy's own, so `refused mid-handshake` was a network
  story for `ada credentials update`. Measured against the real host, and the reason
  it took a real host to find: no fixture had a two-line transcript. Now T10.
- **"`probe_compat` is too small to need a check."** Nothing exercised it, so
  nothing would have caught a `RemoteCommand` reset that stopped being emitted -- and
  a probe whose `true` is suppressed by `ssh_config` never terminates, which is T2
  itself. One `ssh -G` stub that advertises the options, and one that does not.
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
wrapper supplies only process supervision, stderr classification, and backoff. The
python row is now measured rather than assumed: `uv run --script` preserves the exit
status, forwards `TERM` so the handler runs, and hands a grandchild the pty, so
T4/T8/T11 all survive it — but it is not smaller, it loses the keypress window to
`termios`, and `#!/usr/bin/env -S` does not work on this box at all, so the single
executable becomes a trampoline. Lean does not model the operating-system and
network boundary these theorems are about, and the only SSH implementation in the
language is a toy server. `test-ssa` is the proof assistant this problem has. The
full argument, with the bash 4.2 sharp edges that cost real bugs, is in `README.md`.
