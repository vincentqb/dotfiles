# ssa

`ssh` that outlives the network. Waits for the machine to be reachable again and
reconnects, instead of dropping you at a local prompt.

`ssh` already detects a dead link — that is what `ServerAliveInterval` is for —
and then exits. This is the part after "detect".

The name is inherited: `ssa` was a fish abbreviation for
`AUTOSSH_POLL=5 autossh -M 0`, and this replaces it, keeping the muscle memory.
`autossh -M 0` restarts `ssh` blindly whenever it dies — which means it will
re-run a remote command that already half-ran, spin against a changed host key,
and never tell you the certificate expired. Those three differences are most of
what is below.

```fish
ssa --tmux gpu2
```

Close the laptop, change networks, let the VPN drop, let the Midway certificate
expire overnight, reboot the far end: the session comes back.

**It never asks you for anything.** No credential prompt, no `mwinit`, no VPN
dialog, nothing to answer — it waits, tells you what it is waiting for, and
reconnects the moment that thing exists. Fix the cause in another window on your
own schedule; every probe is a fresh `ssh`, so a certificate minted elsewhere
gets picked up without restarting anything.

```
ssa: credentials rejected (certificate expired 10h55m ago) -- retry in 4s (waited 12s)
```

## Why bash

The wrapper's entire job is process supervision plus classifying one child's exit
status and stderr, around a child that must own the terminal. In bash, `ssh` is a
foreground child that inherits the tty directly, so window resizes, escape
characters (`~.`), scrollback and `ProxyJump` need no code at all. The real
"language" here is `ssh -O check`, `ssh-keygen -L`, `curl` — a script that calls
those is the shortest honest expression of the thing, and it runs on a box you
just built, with no interpreter to install first.

| | |
|---|---|
| **bash** | Chosen. Terminal handling is free, the dependencies are the tools it must call anyway, and ~150 lines covers it. Costs: `case` globs as a classifier, and bash 4.2 (Amazon Linux 2) has sharp edges — no `EPOCHSECONDS`, and `"${arr[@]}"` on an empty array is fatal under `set -u`. |
| python | Needs `pty`/`termios`/`signal` work to hand the terminal over cleanly, or `subprocess` with inherited fds — at which point it is this bash script written in Python, plus an interpreter dependency in a tool whose reason to exist is that your connection is broken. Right answer if the classifier ever grows state: per-host history, structured logs, a real state machine. |
| fish | The login shell here, but this must be callable from cron, scripts and other shells, and signal plus process-group handling (`trap`, `wait`, fifos) is more awkward in fish for no gain. |
| lean4 | No. The property worth having — "it always reconnects" — is not a theorem about pure functions; it is about POSIX signals, termios and someone else's router. Lean would fight the IO and the artifact would need a toolchain on every host. |

## What it handles, and how it knows

Two questions decide everything, and `ssh` answers both if you ask precisely:

1. **Whose failure was it?** Exit 255 is ssh's own; any other status came from the
   remote command. So only 255 retries — `exit 3` on the far end still gives 3.
2. **Did a session exist?** ssh's stderr splits cleanly into connect-phase errors
   (`Could not resolve`, `Connection refused`, `No route to host`,
   `ssh_exchange_identification`) and mid-session ones (`closed by remote host`,
   `reset by peer`, `Timeout, server not responding`, `Broken pipe`). That line is
   what makes retrying *safe*.

| Failure | Signal | Response |
|---|---|---|
| Credential expiry | the server says `Permission denied`; `ssh-keygen -L` on the CA cert then explains why, from its hard `Valid: ... to <ts>` | wait. If the cert is *not* expired it says so, rather than implying another `mwinit` would help |
| VPN down | target unreachable while the internet probe is clean, or its name stops resolving | wait, and say which |
| Captive portal | probe URL answers something other than 204 | report it; you still sign in yourself |
| Wifi off, cable out | no global address, or no default route | wait |
| Timeouts, lag | `ServerAlive` fires; a stale `ControlMaster` socket then fails the *next* connect instantly | `ssh -O check`, then `-O exit`, then reconnect |
| Remote reboot | `closed by remote host`, then refused, then the port answers | wait for it, reconnect |
| Host key changed | `REMOTE HOST IDENTIFICATION HAS CHANGED` | **stop.** A rebuilt host and a MITM are identical from here, so `known_hosts` is never rewritten |
| `~.` (you quit) | indistinguishable from a drop — 255, usually silent | a keypress window to stop instead of reconnecting |

Between attempts it probes with a real `ssh` (`BatchMode`, short
`ConnectTimeout`, no mux), so aliases, ports and `ProxyJump` are honoured, but the
screen stays quiet: one status line, backing off 1 s → 30 s, and a bell if the
wait was long enough that you walked away.

Three things it deliberately will not do: rewrite `known_hosts`, re-run a remote
command that may have half-run (`--retry-command` opts in), or run anything on
your behalf to fix credentials, a VPN or a portal.

The cost of never prompting is that a permanently broken login — a wrong
username, a key the host has never seen — looks exactly like a certificate that
is about to be refreshed, so it waits on that forever too. `--max-wait` bounds it
when you want a bound; the status line tells you which one you are looking at.

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
```

| Option | Default | |
|---|---|---|
| `--tmux[=NAME]` | off, `main` | remote tmux session to attach-or-create; implies `-t` |
| `--retry-command` | off | re-run the remote command after a mid-session drop |
| `--max-wait=SECS` | `0` | give up on one reconnect after SECS; 0 waits forever |

Everything else goes to `ssh` untouched. Three more knobs have no flag, only an
env var: `SSA_GRACE` (keypress window before reconnect, default 3s),
`SSA_PROBE_TIMEOUT` (probe `ConnectTimeout`, default 7s), and `SSA_CERT` (cert
read to explain a rejection, default `~/.ssh/id_rsa-cert.pub`). `SSA_MAX_WAIT`
mirrors `--max-wait`.

## Install

```fish
ln -s ~/dotfiles/ssa/ssa ~/bin/ssa
```

## Tests

```fish
./test-ssa
```

27 checks against a stub `ssh` that fails on a script, so the paths that only run
when the network is broken — changed host key, expired certificate, a drop
halfway through a remote command — are exercised while it works. The credential
tests run with stdin closed, because the one thing they assert is that nothing
ever waits on a human.
