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
ssa: waiting for dev-dsk-quennv: credentials rejected (certificate expired 10h55m ago)
```

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
| **bash** | Chosen. Terminal handling is free, the dependencies are the tools it must call anyway, and one executable covers it. Costs: `case` globs as a classifier, and bash 4.2 (Amazon Linux 2) has sharp edges — no `EPOCHSECONDS`, and `"${arr[@]}"` on an empty array is fatal under `set -u`. |
| python | Needs `pty`/`termios`/`signal` work to hand the terminal over cleanly, or `subprocess` with inherited fds — at which point it is this bash script written in Python, plus an interpreter dependency in a tool whose reason to exist is that your connection is broken. Right answer if the classifier ever grows state: per-host history, structured logs, a real state machine. |
| fish | The login shell here, but this must be callable from cron, scripts and other shells, and signal plus process-group handling (`trap`, `wait`, fifos) is more awkward in fish for no gain. |
| lean4 | No. The property worth having — "it always reconnects" — is not a theorem about pure functions; it is about POSIX signals, termios and someone else's router. Lean would fight the IO and the artifact would need a toolchain on every host. |

## What it handles, and how it knows

Two questions decide everything, and `ssh` answers both if you ask precisely:

1. **Whose failure was it?** Any status other than 255 came from the remote
   command and passes through unchanged. Exit 255 is ambiguous when a remote
   command was supplied: the command can itself return 255, and its stderr shares
   a stream with ssh's. Such a command is never retried without
   `--retry-command`, regardless of how its text is classified.
2. **Did an interactive session exist?** ssh's own stderr splits connect-phase
   errors (`Could not resolve`, `Connection refused`, `No route to host`,
   `ssh_exchange_identification`) from mid-session ones (`closed by remote host`,
   `reset by peer`, `Timeout, server not responding`, `Broken pipe`). That
   distinction controls diagnosis and the `~.` keypress window, not command replay.

| Failure | Signal | Response |
|---|---|---|
| Credential expiry | the server says `Permission denied`; `ssh-keygen -L` on the CA cert then explains why, from its hard `Valid: ... to <ts>` | wait. If the cert is *not* expired it says so, rather than implying another `mwinit` would help |
| VPN down | ssh's own `Could not resolve` or `No route to host` | wait |
| Captive portal | probe URL answers something other than 204 while ssh has a connection-class failure | report it; you still sign in yourself |
| Wifi off, cable out | ssh's own `Network is unreachable` | wait |
| Timeouts, lag | `ServerAlive` fires; a stale `ControlMaster` socket then fails the *next* connect instantly | `ssh -O check`, then `-O exit`, then reconnect |
| Remote reboot | `closed by remote host`, then refused, then the port answers | wait for it, reconnect |
| Host key changed | `REMOTE HOST IDENTIFICATION HAS CHANGED` | **stop.** A rebuilt host and a MITM are identical from here, so `known_hosts` is never rewritten |
| `~.` (you quit) | indistinguishable from a drop — 255, usually silent | a keypress window to stop instead of reconnecting |

Between attempts it probes with a real `ssh` (`BatchMode`, short
`ConnectTimeout`, no mux), so aliases, ports and `ProxyJump` are honoured, and a
bell rings if the wait was long enough that you walked away. A probe is a
connection check, not a copy of the session: it clears forwards, removes
session-only flags (`-M`, `-N`, `-s`, `-t`, `-T`, `-O`, `-Q`, `-W`), and resets
`RemoteCommand`/`SessionType` when the client supports them. Without that split,
`-N` suppresses the probe's `true` and a healthy forwarding connection hangs the
recovery loop forever.

**Probing and reporting are on separate clocks**, because they answer to
different things: the probe cadence decides how fast you get back (1 s → 60 s),
and the print cadence decides whether the screen is readable afterwards. A line
per probe is fine for a 30-second outage and unusable for an overnight one —
measured, a nine-hour wait was ~1100 copies of one sentence, each long enough to
wrap, and a wrapped line is what gets shredded when a full-screen program shares
the terminal. So: one line when the wait starts, one whenever the *reason
changes* (DNS gave way to refused; a portal appeared), and otherwise a keep-alive
line every `SSA_NOTE_EVERY` — 55 short lines for that same night. ssh's own
diagnostics still reach you verbatim; ours are one clause and never name the
FQDN, which the wait line already did.

`SIGINT` and `SIGTERM` stop both the active ssh process and the stderr copier;
the wrapper returns 130 and 143 respectively instead of leaving children alive.

Three things it deliberately will not do: rewrite `known_hosts`, re-run any
supplied remote command after an ambiguous exit 255 (`--retry-command` opts in),
or run anything on your behalf to fix credentials, a VPN or a portal.

The cost of never prompting is that a permanently broken login — a wrong
username, a key the host has never seen — looks exactly like a certificate that
is about to be refreshed, so it waits on that forever too. `--max-wait` bounds it
when you want a bound; the status line tells you which one you are looking at.

## Versus autossh

`autossh -M 0` restarts a dropped link with backoff, same as this. It differs
wherever the *reason* for the drop matters. Measured against autossh 1.4g by
pointing `AUTOSSH_PATH` at a stub `ssh` that fails on command:

| | `autossh -M 0` | `ssa` |
|---|---|---|
| Remote command after a drop | re-run: `make deploy` ran **8 times in 25 s**, and would not have stopped | once, then stops (`--retry-command` opts in) |
| Exit status | `exit 7` → **1**. Only 0 and 1 ever come out, and statuses 1 and 2 become *restartable* after the first start | `exit 7` → 7 |
| Clean logout | **1** if the session was shorter than the 30 s gate; 0 once past it | 0 |
| Auth failure, first attempt | stops at once — the gate's whole purpose, and it beats waiting forever | waits (bounded only by `--max-wait`) |
| Auth failure after a good session | the gate no longer applies: **8 silent retries in 25 s**, forever, saying nothing beyond ssh's own `Permission denied` | names it, with how long ago the cert expired |
| `~.` | 255, so it reconnects you to the session you just left | keypress window to stop |
| Changed host key | same split as auth: stops on the first attempt, retries forever after a good session | stops, naming the cause |
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
`ServerAliveInterval` is 0, and this config sets it only for `gpu2`/`gpu3`
(`bastions-config` has a `host *` block, but only for `PubkeyAcceptedKeyTypes`).
On every other host ssh blocks until the kernel gives up on the socket, with
nothing to supervise — the script silently does nothing at all. So `ssa` reads
the effective value and **refuses** when it is 0, naming the fix:

```
ssa: localhost has no ServerAliveInterval, so ssh will never notice a dead link.
    Add to ~/.ssh/config:
        Host localhost
            ServerAliveInterval 30
            ServerAliveCountMax 3
```

Refusing beats supplying one. The setting belongs in `ssh_config`, where plain
`ssh` and `kitty +kitten ssh` benefit too; a wrapper that quietly rewrites
connection parameters on every call is harder to debug later than one error you
fix once. It reads the value `ssh -G` resolves *for that host* and names the
host in the fix, so a per-host block is enough — a `Host *` block covering every
host, or an explicit `-o ServerAliveInterval=…` on the command line, satisfies
it too.

Refusing `-f` is the same lesson from the other end. autossh strips it and forces
`gate_time = 0`; here it made ssh background itself and return 0 immediately, so
`ssa -f -N -L …` exited 0 having supervised nothing and reported success. It is
now refused, pointing at backgrounding `ssa` instead.

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

```fish
ssa gpu2                                # like ssh, but it comes back
ssa --tmux gpu2                         # ... and the session survives too
ssa --tmux=build -J bastion host        # every ssh flag still works
ssa --max-wait=600 gpu2                 # give up on a reconnect after 10m
ssa --retry-command host 'tail -F log'  # opt in to re-running a command
ssa -N -L 8080:localhost:80 host        # supervise a forwarding-only session
```

| Option | Default | |
|---|---|---|
| `--tmux[=NAME]` | off, `main` | remote tmux session to attach-or-create; implies `-t`, forces UTF-8 (`tmux -u`) |
| `--retry-command` | off | re-run the remote command after an ambiguous exit 255 |
| `--max-wait=SECS` | `0` | give up on one reconnect after SECS; 0 waits forever |

The real session receives every other argument unchanged, plus a leading
`-o BatchMode=yes` that callers cannot override. Use plain `ssh` when an
interactive password or confirmation is wanted. The remaining knobs have no
flag, only an env var: `SSA_GRACE` (keypress window before reconnect, default 3s),
`SSA_PROBE_TIMEOUT` (probe `ConnectTimeout`, default 7s), `SSA_CERT` (cert read
to explain a rejection, default `~/.ssh/id_rsa-cert.pub`), `SSA_MAX_DELAY`
(longest gap between probes, default 60s) and `SSA_NOTE_EVERY` (keep-alive line
while the reason is unchanged, default 600s — raise it for a quieter night, set
it very low to watch every probe). `SSA_MAX_WAIT` mirrors `--max-wait`.

## Install

```fish
ln -s ~/dotfiles/ssa/ssa ~/bin/ssa
```

## Tests

```fish
./test-ssa
```

54 checks against local `ssh`, `ssh-keygen`, and `curl` stubs exercise the paths
that normally need a broken network: changed host key, expired certificate,
forwarding-only reconnect, portal diagnosis, ambiguous remote stderr, and direct
`SIGTERM`. The suite makes no network connection and every discovered failure is
kept as a regression.
