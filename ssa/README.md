# ssa

`ssh` that outlives the network. Waits for the machine to be reachable again and
reconnects, instead of dropping you at a local prompt.

`ssh` already detects a dead link — that is what `ServerAliveInterval` is for —
and then exits. This is the part after "detect".

The name is inherited: `ssa` was a fish abbreviation for
`AUTOSSH_POLL=5 autossh -M 0`, and this replaces it, keeping the muscle memory.
[Versus autossh](#versus-autossh) is the honest comparison.

```fish
ssa --tmux gpu2
```

Close the laptop, change networks, let the VPN drop, let the Midway certificate
expire overnight, reboot the far end: the session comes back.

**It never blocks on an SSH prompt.** Every supervised connection forces
`BatchMode=yes`: no password, passphrase, keyboard-interactive, or host-key
question, no `mwinit`, no VPN dialog. It waits, tells you what it is waiting for,
and reconnects the moment that thing exists. Fix the cause in another window on
your own schedule; every probe is a fresh `ssh`, so a certificate minted elsewhere
gets picked up without restarting anything.

```
ssa: waiting for dev-dsk-quennv: cert expired 10h55m ago
ssa: still waiting after 2h30m: cert expired 13h25m ago
ssa: dev-dsk-quennv back after 2h31m, reconnecting
```

## What it guarantees

Eleven properties are what the script is for; everything else is detail. Each is
**discharged by checks in `test-ssa` labelled with its number**, so a failing check
names the property that broke and a property with no check fails the suite outright.
`./test-ssa` is the proof; this table is the index.

| | Property | Why it holds |
|---|---|---|
| T1 | A probe succeeds iff the supervised session would connect | the probe's argv is fixed — the host, and the handful of `-o` values that bound the attempt — [because ssh's own flags are refused rather than filtered](#t1-in-detail), and every connection setting is read from the same `ssh_config` the session reads |
| T2 | Every probe terminates | an appended `true` is what makes a *healthy* probe finite, and `ssh_config` can suppress it two ways: `RemoteCommand` replaces it, `SessionType none` forbids one. Both are reset — but only on a client whose `ssh -G` advertised them, since OpenSSH 7.4 rejects the names. A probe handed to a live master is bounded by none of that, because multiplexed connections ignore `ConnectTimeout`, which is what `PROBE_WALL` (T12) is for |
| T3 | A supplied remote command runs at most once | the guard is on the presence of a command, not on how its text classified: its stderr is this same stream, so it can print anything a classifier looks for. There is no flag to opt out; `--tmux` is how a command survives a drop |
| T4 | Any `ssh` status other than 255 is `ssa`'s status | `exit 7` on the far end gives 7; only 255 is ambiguous enough to be ours |
| T5 | No process `ssa` starts can read from a human | `-o BatchMode=yes` leads both argvs, and `ssh` keeps the first value it obtains, so a later `BatchMode=no` cannot win |
| T6 | A host-key failure stops; `known_hosts` is never written | a rebuilt host and a machine-in-the-middle are indistinguishable from here, so there is no safe automatic answer |
| T7 | A configuration in which `ssh` could not notice a dead link is refused | an effective `ServerAliveInterval` of 0, and `-f`, each make the wrapper a silent no-op — [refused, not patched over](#taken-from-autossh) |
| T8 | `INT`/`TERM` leave no descendant, and exit 130/143 | the handler owns both pids, disarms itself, then terminates and reaps, rather than deferring until the session ends on its own |
| T9 | Every status line is one clause of ≤ 80 columns, and the line count over an outage of length D is at most 2 + D/`NOTE_EVERY` | [two clocks and a width budget](#t9-in-detail) |
| T10 | Every `stderr` maps to exactly one (class, reason), and the two cannot disagree | [one table](#t10-in-detail) |
| T11 | The supervised `ssh` inherits the caller's terminal | `ssh` runs asynchronously so a signal trap can reach it (T8), and bash hands an asynchronous command `/dev/null` for stdin unless a redirection says otherwise. `<&0` is that redirection — one token, and `~.`, resize, scrollback and every full-screen program rest on it. Measured both ways under a pty |
| T12 | Every `ssh` `ssa` starts is bounded | the wait itself is not: a credential that will be refreshed is indefinite, so `^C` is the only bound that means anything. What must terminate is each call — `-O check` has no bound of its own and `ConnectTimeout` does not reach a live master, so both run under `timeout` at `PROBE_WALL`, [without which one wedged probe *is* the whole wait](#t12-in-detail) |
| T13 | No descendant can delay a probe or the diagnosis | a `ProxyCommand` grandchild inherits `ssh`'s stderr, and `timeout` kills the `ssh` it started, not that child. So a probe writes stderr to a file rather than a `$(...)` pipe that would wait for the write end to close, and the session's `tee` — which never sees EOF while the child lives — is drained for a bounded time and then stopped. Everything needed was written before `ssh` exited |

Four of them earn more than a line.

### T1 in detail

This is the one whose two directions fail differently. If the probe is **stricter**
than the session, `ssa` waits for something that is not actually blocking it — the
failure mode of "it stopped reconnecting". If it is **laxer**, `ssa` reconnects
into an instant failure and spins.

It used to be kept true by *filtering* the caller's argv: 42 lines of hand-rolled
getopt deciding, flag by flag, which of ssh's own options a probe may keep, which
it must drop, and which take an argument that has to be consumed with them. Every
one of those decisions was a chance to fail in one of the two directions above.

So the flags are refused instead, and the probe's argv is fixed:

```
ssh -T -o BatchMode=yes -o ConnectTimeout=7 -o ControlMaster=no \
    -o ClearAllForwardings=yes [-o RemoteCommand=none -o SessionType=default] host true
```

| What the probe carries | Why it cannot change reachability |
|---|---|
| `-o ConnectTimeout` | bounds the attempt |
| `-o BatchMode=yes` | the session forces it too (T5) |
| `-T` | shape of the session, not of the connection |
| `true` | the session's payload is not what we are testing |
| `-o ControlMaster=no` | declines to *become* a master; still *uses* one |
| `-o ClearAllForwardings=yes` | a forward that cannot bind warns, it does not fail a connect |
| `-o RemoteCommand=none`, `-o SessionType=default` | only when `ssh -G` advertises them; either would suppress `true` |

Everything else — the port, the identity, `ProxyJump`, the cipher, the forwards —
lives in `ssh_config`, which both the probe and the session read, so the two agree
by construction rather than by a filter. `test-ssa` still reads the probe's real
argv and fails on any seventh `-o`.

Note what is **not** in that list: `ControlPath`. A probe that overrides it opens a
fresh handshake, and on a host reached through a `ProxyCommand` — `ProxyJump`, a
Midway bastion, `aws ssm start-session` — a fresh handshake needs credentials that
a live master does not. Override it and `ssa` waits for `mwinit` on a host it could
have reconnected to over the existing socket. Measured against a stub proxy whose
credentials had expired, with the master still alive:

| | probe result | proxy invoked |
|---|---|---|
| probe with `ControlPath=none` | 255, `ssh_exchange_identification` | yes |
| probe with the session's `ControlPath` | 0 | no |
| **the session itself** | **0** | **no** |

The middle row is the one that agrees with the session, so the probe inherits
`ControlPath`. Staleness is handled where it belongs and *before* the probe loop:
`stale_master` runs `-O check`, then `-O exit`, so a probe reaches a live master or
none. That ordering is itself a check, because it is what makes inheriting the path
safe.

### T9 in detail

**The count.** Probing and reporting are on separate clocks, because they answer to
different things: the probe cadence decides how fast you get back (1 s → 60 s), the
print cadence decides whether the screen is readable afterwards. A line per probe
is fine for a 30-second outage and unusable for an overnight one: nine hours at the
60 s cap is ~540 copies of one sentence. So: one line when the wait starts,
one whenever the *reason changes* (DNS gave way to refused; a portal appeared), and
otherwise a keep-alive line every `NOTE_EVERY` — 55 lines for that same night.

What "changed" means is not obvious, and getting it wrong silently costs the whole
property. A reason worded with a duration — `cert expired 12m30s ago` — is a
*different string* on every probe, so comparing the rendered reason reports a change
every time and `NOTE_EVERY` throttles nothing. Measured before the fix: five
lines in twelve seconds where this predicts two. So the comparison is against the
reason with the ticking part removed, and only the printing uses the rendered one.

**The width.** A wrapped line is the one a full-screen program sharing the terminal
shreds, so a status line that wraps is a self-inflicted instance of the bug the
cadence exists to avoid. "Status line" is the whole scope of the claim: a refusal
that exits may spend more room, and the `ServerAliveInterval` one deliberately
prints a config block. Every line has one shape, `ssa: <state>: <reason>`, and
that fixes a budget: 80 columns, less `ssa: waiting for `, less a 20-character host
label, less `: ` — 41 characters for the reason. `test-ssa` recomputes that
arithmetic, holds every row of the failure table to it, checks that `REASON_MAX` —
the cap on wording `ssh` chose rather than us — agrees, and renders **every shape at
its worst case**. That last check is the one that matters: a version that sampled
one real run saw nothing while the give-up line was reaching 97 columns. It is why
that line reports the outcome and not the reason, which the line above it already
carried. Durations carry hours for the same reason: `10h55m`, never `655m00s`.

### T10 in detail

There is one table. A row is `class|clause|substring`: the class decides what `ssa`
does, the clause is what you read, and they are the same row, so no edit can make
the decision and the sentence drift apart. A new failure mode is one row — it used
to be three edits in three `case` statements that each carried their own copy of
the pattern list.

First match wins **by row**, which is how a proxy's own diagnostic outranks the
generic handshake failure `ssh` reports underneath it: an expired SSM token reads
`proxy credentials expired`, not 41 truncated characters of a botocore traceback.
The same ordering is why a 403 from `aws ssm start-session` reads
`proxy rejected, refresh AWS credentials` — measured against the real host, it used
to read `refused mid-handshake`, a network story for a credentials problem, and
being a connect class it then went looking for a captive portal that was not there.

What is searched is the **last `TAIL_LINES` lines**, not the whole stream. A
session's stderr is shared: the remote command writes to it, a host with
`StrictHostKeyChecking` off warns on every connect, and `ssh -v` reports a refusal
for each address it tries before connecting through another one. Search all of it
and a drop gets diagnosed from a line left by an attempt that recovered — reported
as `connection refused`, sent down the connect path, and refined with a portal
guess. Three lines is the depth a real transcript needs: a proxy's diagnostic plus
the handshake line under it, and one of slack.

Unmatched stderr is a mid-session death, whose own last line is the reason, capped
to fit T9.

The table is data, so the checks read it rather than sampling it: no pattern may
appear twice, every row must be a known class with three fields, every clause must
fit T9's budget, and **every row is driven end to end in one loop** — so a row
added later is proven the moment it is added.

### T12 in detail

`ssa` waits forever, on purpose. A certificate that will be refreshed, a VPN that
will come back and a closed laptop are all indefinite, and the caller is a person
at a terminal: `^C` is the bound that means something, and a wrapper that gave up
on its own is a wrapper you restart by hand. `--max-wait` existed, was never
passed, and is gone.

So the bound that matters is **per call**, because without one a single wedged
probe *is* the whole wait. Three calls had no bound of their own:

| Call | Its own bound, before | Worst case |
|---|---|---|
| `ssh -O check` / `-O exit` | none at all | as long as the master takes |
| a probe reaching a live master | none — multiplexed connections ignore `ConnectTimeout` | that master's keepalive, so `60 × 5` was 5 minutes here |
| the portal check | `curl --max-time 5` | 5s per probe, added to the wait it is describing |

Each now runs under `timeout`. The two constants answer different questions.
`PROBE_CONNECT` (7s) is `ConnectTimeout`, which lets `ssh` explain itself — a bound
`ssh` knows about produces `connection timed out`, not silence. `PROBE_WALL` (15s)
is a kill for the paths `ConnectTimeout` cannot reach, so it has to be the larger of
the two or it would fire first and take the diagnosis with it. A probe killed by it
says so, because a fragment of an incomplete handshake is not a reason.

The check drives a stub that never returns, against a copy of the script carrying
`PROBE_WALL=1`, and counts probes in the window: bounded, several happen; unbounded,
the first one consumes it.

## The four things it does beyond reading stderr

`ssh` answers most questions if you ask precisely, and the table in `ssa` is that
asking. Four cases need a second source:

| | Question `ssh` cannot answer | How |
|---|---|---|
| Credential expiry | *why* was permission denied? | `ssh-keygen -L` on the cert, against its hard `Valid: … to <ts>`. If the cert is live it says so, rather than implying another `mwinit` would help. If there is no cert to read it says nothing — `date -d ''` returns midnight today, so a missing cert used to be reported as expired, in wording indistinguishable from the true message |
| Captive portal | is something answering *for* the network? | a probe URL returns other than 204 while `ssh` has a connection-class failure. Reported, never signed into for you |
| Stale multiplexing | did the master die with the link? | `-O check`, then `-O exit`, before probing (T1), under the same clock as everything else (T12) |
| `~.` | did you quit, or did the link? | both are a silent 255. A keypress window before reconnecting — and the key is **named**, because a dying full-screen program leaves escape bytes in the input queue and those are not someone asking to stop |

Three things it deliberately will not do: rewrite `known_hosts` (T6), re-run a
supplied remote command after an ambiguous 255 (T3), or run anything on your
behalf to fix credentials, a VPN or a portal.

The cost of never prompting is that a permanently broken login — a wrong
username, a key the host has never seen — looks exactly like a certificate that
is about to be refreshed, so it waits on that forever too. The status line tells
you which one you are looking at, and `^C` is how you stop it.

## Why bash

The wrapper's entire job is process supervision plus classifying one child's exit
status and stderr, around a child that must own the terminal. In bash, `ssh` is a
child that inherits the tty directly, so window resizes, escape characters
(`~.`), scrollback and `ProxyJump` need no terminal emulation. The real
"language" here is `ssh -O check`, `ssh-keygen -L`, `curl` — a script that calls
those is the shortest honest expression of the thing, and it runs on a box you
just built, with no interpreter to install first.

| | |
|---|---|
| **bash** | Chosen. Terminal handling is free, the dependencies are the tools it must call anyway — `ssh`, `ssh-keygen`, `curl`, `timeout` — and one executable covers it. Costs: substring matching against a table rather than a real parser, and bash 4.2 (Amazon Linux 2) has sharp edges — no `EPOCHSECONDS`, `"${arr[@]}"` on an empty array is fatal under `set -u`, and an asynchronous command gets `/dev/null` for stdin unless a redirection says otherwise. |
| python | Measured, not assumed. `uv run --script` passes an exit status through unchanged, forwards `TERM` so the handler runs and the grandchild is reaped, and hands a grandchild the pty — T4, T8 and T11 all survive it, at 46 ms of startup. It would win in one structural place: `Popen(stderr=PIPE)` plus a reader thread and a `deque(maxlen=3)` replaces the fifo, the `tee`, the bounded drain and the tail, making T13 *unrepresentable* rather than fixed. It loses the keypress window to `termios`, and on this box `#!/usr/bin/env -S` does not work at all — `/usr/bin/env` is coreutils 8.22 — so "one executable file" becomes a trampoline. Net: not smaller, modestly more robust. Right answer once the classifier grows state: per-host history, structured logs, a real state machine. |
| fish | The login shell here, but this must be callable from cron, scripts and other shells, and signal plus process-group handling (`trap`, `wait`, fifos) is more awkward in fish for no gain. |
| lean4 | No. T1 through T13 are properties of POSIX signals, termios and someone else's router, not about pure functions. Lean would fight the IO and the artifact would need a toolchain on every host — and the only SSH implementation in the language is a toy server. `test-ssa` is the proof assistant this problem has. |

## Versus autossh

`autossh -M 0` restarts a dropped link with backoff, same as this. It differs
wherever the *reason* for the drop matters. Measured against autossh 1.4g by
pointing `AUTOSSH_PATH` at a stub `ssh` that fails on command:

| | `autossh -M 0` | `ssa` |
|---|---|---|
| Remote command after a drop | re-run: `make deploy` ran **8 times in 25 s**, and would not have stopped | once, then stops (T3) |
| Exit status | `exit 7` → **1**. Only 0 and 1 ever come out, and statuses 1 and 2 become *restartable* after the first start | `exit 7` → 7 (T4) |
| Clean logout | **1** if the session was shorter than the 30 s gate; 0 once past it | 0 |
| Auth failure, first attempt | stops at once — the gate's whole purpose, and it beats waiting forever | waits, and says what for |
| Auth failure after a good session | the gate no longer applies: **8 silent retries in 25 s**, forever, saying nothing beyond ssh's own `Permission denied` | names it, with how long ago the cert expired |
| `~.` | 255, so it reconnects you to the session you just left | keypress window to stop |
| Changed host key | same split as auth: stops on the first attempt, retries forever after a good session | stops, naming the cause (T6) |
| Captive portal | invisible | reported |

The row that matters here is the second-to-last. A 20 h Midway certificate
expires *during* a session's life, which is precisely when autossh's gate has
stopped protecting — so the failure it handles worst is the one that happens
daily.

### Taken from autossh

`-M <port>` passes traffic through a forwarded port to catch a connection that is
hung but still alive. `ServerAliveInterval` supersedes it — which is why the
abbreviation used `-M 0` — but the underlying point generalises: **nothing
reconnects if nothing notices the link died.** ssh's default
`ServerAliveInterval` is 0, and on this machine only the `gpu2`/`gpu3` include
sets it. On every other host `ssh` blocks until the kernel gives up on the socket,
with nothing to supervise — the script silently does nothing at all. So `ssa`
reads the effective value and **refuses** when it is 0, naming the fix:

```
ssa: localhost has no ServerAliveInterval, so ssh will never notice a dead link.
    Add to ~/.ssh/config:
        Host localhost
            ServerAliveInterval 15
            ServerAliveCountMax 3
```

Refusing beats supplying one. The setting belongs in `ssh_config`, where plain
`ssh` and `kitty +kitten ssh` benefit too; a wrapper that quietly rewrites
connection parameters on every call is harder to debug later than one error you
fix once. It reads the value `ssh -G` resolves *for that host* and names the
host in the fix, so a per-host block is enough — a `Host *` block covering every
host, or an explicit `-o ServerAliveInterval=…` on the command line, satisfies
it too.

The *value* matters as much as its presence, and only the host's own config can
set it. `ServerAliveInterval` × `ServerAliveCountMax` is how long `ssh` keeps a
dead link before terminating the session, and nothing here can reconnect sooner
than that: the `60 × 5` the SSM hosts started with is five minutes of sitting in a
session that is already gone, which is most of what "it does not reconnect very
well" turns out to mean. `15 × 3` is 45 seconds.

Refusing `-f` is the same lesson from the other end. autossh strips it and forces
`gate_time = 0`; here it made ssh background itself and return 0 immediately, so
`ssa -f -N -L …` exited 0 having supervised nothing and reported success.

`AUTOSSH_GATETIME` is the third idea and the one not taken: it would stop a
*first* attempt that dies instantly, which is the deliberate opposite of waiting
for a certificate you are about to refresh.

## Reconnecting is not resuming

A new connection is a new shell. Only the far end can keep your work, so
`--tmux[=NAME]` attaches-or-creates a named session (`tmux new -A`, tmux ≥ 2.0)
and every reconnect lands back in it. Without it you get a fresh login.

The equivalent in `ssh_config` — what [`../ssh/ssh/config`](../ssh/ssh/config)
does for `emr` — is `RemoteCommand` plus `RequestTTY force`; `--tmux` is the same
idea without needing OpenSSH ≥ 7.6, which matters on Amazon Linux 2 (7.4p1).

## Usage

Two options and a host. Everything else that used to be a setting is a constant in
the script, because each was a knob nobody turned and an option is a thing to get
wrong at 2am on a broken link.

```fish
ssa ddsk                                # like ssh, but it comes back
ssa --tmux=0 ddsk                       # ... and the session survives too
ssa --tmux=build gpu2                   # a named session
ssa ddsk uptime                         # a remote command, run at most once
```

| Option | Default | |
|---|---|---|
| `--tmux[=NAME]` | off, `main` | remote tmux session to attach-or-create; implies `-t`, forces UTF-8 (`tmux -u`) |

**ssh's own flags are refused**, naming the flag and pointing at `~/.ssh/config`.
That is not a limitation being apologised for: it is what makes T1 hold by
construction rather than by a filter, and every one of those flags has a
`ssh_config` spelling that plain `ssh` and `kitty +kitten ssh` read too. A
forwarding-only session is `SessionType none` plus `LocalForward` in a `Host`
block, which survives a reconnect without `ssa` passing anything.

A supplied remote command is never replayed after an ambiguous 255 (T3) and there
is no flag to ask for one: run it under `--tmux` if it has to survive a drop.

It waits forever (T12). `^C` is the bound.

`timeout(1)` from coreutils is required — it is what bounds a probe — and
`gtimeout` is accepted where that is the name it has.

## Install

```fish
ln -s ~/dotfiles/ssa/ssa ~/bin/ssa
```

## Tests

```fish
./test-ssa
```

95 checks against local `ssh`, `ssh-keygen` and `curl` stubs. Each one that
discharges a property is labelled with its number, so a failure names the property
that broke; the rest cover the interface and the gate itself. They exercise the
paths that normally need a broken network: a changed host key, an expired
certificate, a live control master behind expired proxy credentials, portal
diagnosis, an SSM 403 under a handshake failure, a stale line from an attempt that
recovered, ambiguous remote stderr, an escape sequence left in the input queue, a
probe and a control socket that never come back, a descendant that keeps `ssh`'s
stderr open after `ssh` has gone, and a direct `SIGTERM`.

Three kinds of check, in increasing order of how long they stay true:

- **behavioural** — drive `ssa` and read what it did (most of them);
- **argv** — read the argv the stub was called with, which is how T1's fixed probe
  and T2's compatibility resets are held to the claim rather than to a habit;
- **data** — read the failure table back out of the script and hold the data
  itself to T9's column budget and T10's uniqueness, so a new row cannot break a
  theorem without a check going red.

`ssa` has no runtime knobs, so a check that needs a different clock or a stub
certificate does not get one: it either points `HOME` at the scratch directory, or
generates a copy of the script with one constant rewritten — and that rewrite fails
loudly unless it matches exactly one line, so a renamed constant cannot leave a
check silently testing nothing.

Two of them are **wall-clock**: T12 and T13 assert that a wedged call is cut off
and that a live grandchild does not stall the loop. Those are the ones that fail on
a loaded machine before they fail on a real defect, so they assert *that the loop
kept running* rather than an exact duration.

The suite makes no network connection. `T11` needs a pty and is skipped, loudly,
without `python3`.

Nothing in the gate is a habit. `bash -n` and `shellcheck` are the suite's own first
two checks, two more compare the `T<n>` labels here against the ones in the table
above so neither can drift, and the repo's `.pre-commit-config.yaml` runs the whole
suite whenever `ssa/` changes. Every discovered failure is kept as a regression.
