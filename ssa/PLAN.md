# `ssa` design record

## Goal

Wrap OpenSSH so an interactive shell or tmux attachment reconnects after credential
expiry, VPN loss, captive portals, timeouts, network changes, and remote reboots.
Preserve OpenSSH's terminal behaviour and configuration instead of replacing either
— and take a host, not a copy of ssh's command line: every connection setting
belongs in `ssh_config`, where the probe and the session both read it.

## The gate

T1–T14 are stated in `README.md`; that table is the index and is not repeated here.
This file holds the rules that keep them true.

> **Every property names the check that discharges it, and every check that
> discharges one says which. A property with no check is a claim.**

> **Every property has a mutant in `mutants.sh`.** Break the property, and the
> check must go red. A check that survives its mutant is decoration, and the
> mutation run is the only thing that tells you which kind you have.

The second rule is newer and earned its place immediately: T8's `SIGCONT`-before-
`SIGTERM` claim had a check that passed with `SIGCONT` removed, because the kill
fallback ended the child either way. The check now asserts that the child *handled*
the signal — a file the stub writes from its own `SIGTERM` handler — which is the
part that only happens if something resumed it first.

Prefer a check that reads **data or argv** over one that samples behaviour, because
that is the class a plausible-looking edit cannot slip past. `RULES` is read out of
the module and driven end to end; `PROBE_OPTS` is read as the probe's real argv.

T12 and T13 are the exception that has to sample behaviour: a bound is a claim about
the clock, so the only way to check it is to point `ssa` at something that will not
come back and watch what it does next. They assert that the loop kept running rather
than an exact duration, so a loaded machine does not read as a regression.

## Why Python, when bash worked

Bash was the right first answer and stopped being the right one at T13. The full
argument is in `README.md` § Why Python. The short version: streaming stderr live
while keeping its tail needed a fifo, a `tee`, a bounded drain and a `tail` in bash,
and all four existed because a `ProxyCommand` grandchild can hold a pipe open. In
Python that is a `select` loop and a `deque`. The rewrite is *larger* (667 lines
against 397) and buys a pure classifier, an injected clock, and a suite that no
longer `sed`-rewrites constants into a copy of the script to reach a path.

`uv run --script` was measured for the PEP-723 shape and is not used: this needs no
third-party dependency, so `#!/usr/bin/env python3` is one less moving part.

## Kept deliberately short

Not defects, and not worth the code they would take here:

- `stop` signals the `ssh` it started and any in-flight probe, not a `ProxyCommand`
  grandchild. Reaching one means a process group, and putting the session in a new
  session is exactly what T11 depends on *not* doing. T13 covers the part that
  costs something — such a child cannot delay us.
- The classifier is substring matching against a table, so `ssh -v` output remains
  something it reads by luck rather than by grammar. `TAIL_LINES` keeps luck from
  compounding; a real parser would mean the debug-output dependency this avoids.
- Refusing ssh's flags means a setting with no `ssh_config` spelling cannot be
  passed at all. There is no such setting among the ones this is used with, and the
  refusal names the flag, so the failure is a sentence rather than a silent
  difference between the probe and the session.
- A suspended remote tmux client cannot be rescued from this side. The fix is in
  `../tmux3/tmux.conf`, which unbinds `suspend-client`.

## Superseded

Kept because each was a real belief that a check now contradicts. Deleting them
invites the same edit twice.

- **"A probe must be a filtered copy of the caller's argv."** 42 lines of
  hand-rolled getopt, each decision able to fail in either direction, both silent —
  stricter and `ssa` waits out an outage that is not happening, laxer and it
  reconnects into an instant failure. ssh's flags are refused now, and the probe's
  argv is fixed. Now T1.
- **"Every timing knob wants an env var, and a wait wants a bound."** Nine knobs, of
  which one was ever passed. `--max-wait` gave up on a wait only a person can judge.
  Constants now. What must terminate is each *call*, which is T12.
- **"`--max-wait` is checked often enough."** It was read *between* calls, and then a
  call was made that had no obligation to return: `-O check` has no bound of its own,
  and `ConnectTimeout` does not apply to a connection handed to a live master. Now
  T12.
- **"ssh exiting means its stderr has reached us."** A `ProxyCommand` descendant
  inherits fd 2, so the write end outlives `ssh` and a reader never sees EOF. Killing
  does not help — it reaches the process you started, not that child. Bounded drain
  for the session, a file rather than a pipe for the probe. Now T13.
- **"A reader thread is the obvious way to stream and keep stderr."** It is, and it
  reintroduces the same bound one level down: a thread blocked in `readline()` holds
  the pipe's lock, and closing the pipe waits for that lock, so a grandchild's
  45-second sleep became a 45-second deadlock. `select` owns the loop instead. Now
  T13, and the reason its check times `ssa` through a *file* — capturing through a
  pipe times the harness's own drain, which read as a 46-second failure against a
  wrapper that had already finished.
- **"`argparse` can express this CLI."** `--tmux` with an optional argument consumes
  the next token, so `ssa --tmux gpu2` parsed as *session* `gpu2` and no host. The
  option takes its value with `=` only, and the pass is hand-rolled. Now checked by
  a mutant that stops `--tmux` from matching.
- **"The whole of stderr is the right thing to search."** It is shared: the remote
  command writes to it, a host with `StrictHostKeyChecking` off warns on every
  connect, and `ssh -v` reports a refusal per address before connecting through
  another. So a drop was classified from a line left by an attempt that recovered.
  Only the last `TAIL_LINES` lines. Now T10.
- **"A 403 from the SSM proxy is a handshake refusal."** It is the generic line `ssh`
  prints underneath the proxy's own, so `refused mid-handshake` was a network story
  for `ada credentials update`. Now T10.
- **"`probe_resets` is too small to need a check."** Nothing exercised it, so nothing
  would have caught a `RemoteCommand` reset that stopped being emitted — and a probe
  whose `true` is suppressed never terminates, which is T2 itself.
- **"A probe should bypass multiplexing, so a stale socket cannot fake a healthy
  host."** Half right, and the wrong half was load-bearing: `ControlPath=none` made
  the probe stricter than the session, so on a proxied host it demanded credentials
  the session did not need. Staleness belongs to `drop_stale_master`, which runs
  before the probe loop. Now T1.
- **"Three `case` statements over the same stderr are fine, they are small."** Each
  carried its own copy of the pattern list, so a class and its sentence could
  disagree. One table. Now T10.
- **"A duration is minutes and seconds."** An overnight wait read `655m00s`. Now T9.
- **"The reason is a string; compare it to see whether it changed."** A reason worded
  with a duration is a different string on every probe, so the comparison reported a
  change every time and the cadence throttled nothing: five lines in twelve seconds
  where T9 predicts two. `Diagnosis.key` is what "changed" means now.
- **"A width check on a real run's output is enough."** It saw nothing while the
  give-up line reached 97 columns. Every shape is now rendered at its worst case from
  the budget arithmetic, which is a property of the grammar rather than of a fixture.
- **"If `ssh-keygen` says nothing, `date` will fail and we return no note."**
  `date -d ''` succeeds and returns midnight today, so an unreadable certificate was
  reported as `cert expired 19h55m ago` — a false reason indistinguishable from the
  true one. A missing certificate returns nothing.
- **"A probe may as well carry the user's `-q` and `-E`."** Both silence or redirect
  the stream the diagnosis is read from.
- **"Any key stops the reconnect."** A dying full-screen program leaves escape bytes
  in the input queue; a mouse report was aborting the reconnect. The key is named.
  Now T11.
- **"An unrecognised reason may be capped at 64 characters."** That made the status
  line wrap, which is the failure the separate print cadence exists to avoid. The cap
  is derived from the line grammar and checked against it.
- **"A cert note explains any rejected credential."** `Too many authentication
  failures` is not a cert expiry, and saying it was sent you to `mwinit` for nothing.
  The note is attached to one row, not to a class. Now T10.
- **"`ssh`'s `ServerAliveInterval` is the only in-session detector a session
  needs."** The alias this replaces began as `autossh -M <port>` — a live
  monitor loop, polled every 5 seconds — and was quietly degraded to `-M 0`
  before the first rewrite, which then cited the degraded alias as evidence the
  monitor was redundant. Three things defeat the keepalive, all real here: a
  multiplexed session's keepalive belongs to the *master*, which keeps whatever
  values it started with; the monotonic clock it is scheduled on stops during a
  suspend, so an overnight death is noticed interval × countmax of *awake* time
  after the lid opens; and the product is per-host config, 45 seconds to five
  minutes across this machine's hosts. "The screen is just frozen" was all
  three. The watchdog probes on its own clock and drops the session itself; an
  `AUTH` probe failure resets the count rather than adding to it, because a
  refusal proves the path is up and a certificate expires mid-session daily.
  Now T14.
- **"A stopped child still reaps on `SIGTERM`."** It does not: `TERM` stays pending
  while the process is stopped, so the wrapper's kill fallback ended it and `ssh`
  never restored the terminal. `SIGCONT` precedes `SIGTERM`. Now T8 — and the first
  property whose check was found by mutation rather than by a failure.
