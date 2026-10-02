# ssa recovery design

## Investigation, 2026-10-02

The previous implementation's 65 tests passed, but the tests did not model the
identity of an SSH transport. Several claims in the README were stronger than
the implementation:

1. On a host without multiplexing, the watchdog opened a separate SSH connection.
   Success established that another connection worked, while the supervised
   connection could remain frozen.
2. `ControlMaster=no` did not require using the configured socket. OpenSSH could
   silently fall back to a new connection.
3. `ssh -O check` checked the local master, not traffic to the remote server.
   A frozen remote connection could have a locally responsive master.
4. Only timeout and CONNECT-class results counted as failed heartbeats. Resets,
   broken pipes, empty diagnostics, and proxy authentication failures could
   repeat indefinitely without recovery.
5. EOF on stderr ended the monitor loop and entered an unbounded process wait.
   A still-running SSH process no longer received heartbeats. Continuously
   readable stderr could instead prevent noticing process exit.
6. Configuration lookup and initial connection setup were not fully supervised.
   The readiness timeout could also be shorter than a configured SSM handshake.

Local process reproductions confirmed the classification and stderr failures
before the changes. OpenSSH's manual and source confirmed the multiplexing
fallback behavior.

## Connection ownership

Every session attempt gets a private temporary control socket. Force
`ControlMaster=yes` and `ControlPersist=no`; keep SSH in the foreground, including
overriding `ForkAfterAuthentication` on clients that advertise it.

This costs connection sharing with other invocations. It provides a transport
the wrapper can identify and terminate without disrupting unrelated sessions.
An existing shared master is never declared stale or killed by `ssa`.

The private socket starts listening after authentication. Until then, enforce a
setup deadline instead of treating process creation as a successful connection.

## Heartbeats and readiness

A heartbeat executes `true` on the owned socket. Pair `ControlMaster=no` with
`ProxyCommand=false`: if multiplexing fails, fallback cannot open a different
transport. A command-line ProxyCommand takes precedence over configured ProxyJump
in OpenSSH, including the installed 7.4 client.

No authentication happens on a healthy existing transport, so heartbeat failure
does not need an exemption for expired credentials. Every nonzero result counts;
two consecutive failures trigger recovery, and success resets the count.

After disconnection, readiness deliberately uses a fresh transport. This matches
the next session's new connection. Respect the configured handshake timeout,
with an outer process deadline covering DNS, proxy startup, and authentication.

Reset `RemoteCommand` and `SessionType` in probes only when the installed client
advertises them. Suppress probe forwarding, TTY allocation, local commands, and
prompts. Keep the user session's remote command and forwarding configuration.

## Process and terminal lifecycle

Poll the SSH process and advance the watchdog independently of stderr readiness.
EOF disables further reads, not supervision. After process exit, bound the
remaining drain even when another process continues writing stderr.

Use files for probe diagnostics so inherited pipes cannot prolong collection.
Run probes/configuration checks in their own process groups for timeout cleanup.
The actual session keeps the caller's terminal and foreground process group.

Resume a stopped SSH child before TERM. Reap it after a KILL fallback and restore
the terminal settings saved before that attempt. Do not claim this terminates
arbitrary detached proxy descendants.

Detect a wall/monotonic clock gap after suspend, schedule an immediate heartbeat,
and expire any heartbeat that was already in flight.

## Verification and limits

Process stubs cover failure classification and lifecycle edges. Opt-in real SSH
tests additionally exercise multiplexing, blocked transport, failed fallback,
expired proxy credentials, and a complete reconnect. Accelerated watchdog timers
keep those tests short while native SSH keepalives remain slow.

Mutation checks use temporary copies, validate their replacement anchors, and
check the selected tests on the original source first. A broken mutation harness
must not be mistaken for a detected regression.

Connection health is not application health. An extra SSH channel may work while
the shell or tmux client is stopped. Conversely, a restricted server may reject
that channel while its original session works. These limits, connection-sharing
costs, and timing qualifications belong in the README.

Source references and comparisons with autossh and mosh are in the README.
