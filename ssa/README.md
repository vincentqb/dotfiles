# ssa

An OpenSSH supervisor that detects an unresponsive connection and reconnects an
interactive shell or tmux attachment. Python 3.10+, standard library only.

```sh
ssa --tmux gpu2
```

Use tmux to keep remote work across reconnects. Without tmux, reconnecting opens a
new shell; it cannot restore the old shell's processes.

## Usage

```sh
ssa ddsk                           # reconnect an interactive shell
ssa --tmux ddsk                    # attach or create tmux session "main"
ssa --tmux=build gpu2              # attach or create a named session
ssa ddsk uptime                    # run a command once
ssa --help
```

`--tmux` takes a name with `=`, so `ssa --tmux gpu2` means the default tmux session
on host `gpu2`. It forces a terminal and runs `tmux -u new-session -A`.

Connection settings such as ports, identities, ProxyJump, ProxyCommand, and
forwarding belong in `~/.ssh/config`. SSH command-line flags before the hostname
are refused. Arguments after the hostname are the remote command.

Configure native SSH keepalives too; an effective `ServerAliveInterval 0` is
refused:

```sshconfig
Host gpu2 ddsk
    ServerAliveInterval 15
    ServerAliveCountMax 3
```

The wrapper uses `BatchMode=yes`, so SSH authentication and host-key questions
cannot block recovery. Refresh credentials or restore the VPN in another window.
It waits until a new connection works, or until you stop it. A proxy program can
have its own prompting behavior; the connection setup deadline bounds that wait.

```text
ssa: waiting for dev-dsk-quennv: cert expired 10h55m ago
ssa: still waiting after 2h30m: cert expired 13h25m ago
ssa: dev-dsk-quennv back after 2h31m, reconnecting
```

Inside the session, SSH owns stdin and stdout, preserving terminal behavior and
escape sequences. To force a reconnect, type Enter, then `~.`. After an ambiguous
disconnect, press `q` during the three-second window to stop reconnecting. During
the retry wait, Ctrl-C stops the wrapper. A normal logout ends it.

Install with:

```sh
ln -s ~/dotfiles/ssa/ssa ~/bin/ssa
```

## How recovery works

Each attempt starts a foreground SSH master with a **private control socket** in
a new mode-0700 temporary directory. `ControlPersist` is disabled for that attempt.
This applies even when the host normally has multiplexing disabled or shares a
long-lived master.

There are two different checks:

| Check | What it establishes | How |
|---|---|---|
| Heartbeat while connected | This session's SSH transport can open a channel and run `true` | Use the attempt's private socket; `ProxyCommand=false` prevents fallback to a new connection |
| Readiness after disconnection | A fresh login can run `true` | Disable multiplexing with `ControlPath=none`, using the host's normal connection and proxy settings |

An existing session's heartbeat does not authenticate again, so an expired local
certificate or proxy token alone does not disconnect it. A reconnect establishes
a new transport and needs valid credentials. The wrapper does not reuse or
terminate masters belonging to other SSH sessions.

The heartbeat runs every 20 seconds, with a 15-second deadline. Two consecutive
failures trigger shutdown and recovery; a success resets the count. Timeouts,
resets, broken pipes, and silent nonzero exits all count. Detection normally takes
at most roughly **55 seconds while running**, plus scheduling and shutdown time;
SSH's own keepalive may end the connection sooner.

A detected suspend/resume clock gap schedules an immediate heartbeat and expires
any heartbeat left over from before sleep. No monitor can run while the machine
is suspended.

Connection setup is monitored separately. Starting the SSH process does not mean
authentication succeeded: the private master must begin listening. Setup and
fresh readiness checks have a deadline of at least 45 seconds, extended to the
configured `ConnectTimeout` plus 15 seconds when necessary. If no positive
`ConnectTimeout` is configured, readiness uses 30 seconds. This allows slower SSM
handshakes that the old seven-second readiness timeout rejected.

Failed readiness checks back off from 1 to 60 seconds **between attempts**. Failed
attempts themselves take time too. The retry loop has no overall time limit.
`ssh -G` configuration lookup has a 15-second process deadline.

The process monitor remains active after stderr closes. Once SSH exits, stderr
is drained for at most one second, even if a descendant still holds or writes the
pipe. Shutdown resumes a stopped SSH child before sending TERM, then escalates to
KILL if necessary. The wrapper restores the terminal settings even after KILL.

## Limits

- **A healthy SSH transport does not prove the foreground application is healthy.**
  A stopped tmux client, a hung shell, or terminal flow control can leave the
  screen frozen while heartbeats succeed. Enter followed by `~.` forces recovery;
  use Ctrl-Q if output was paused by Ctrl-S.
- The server must permit an additional session channel and a `true` command.
  `MaxSessions 1`, forced commands, and restricted SSH servers may reject
  heartbeats despite a working transport.
- Readiness does not validate the eventual remote application, tmux startup, or
  every forwarding binding. They can still fail after a successful check.
- A supplied remote command is never replayed after exit 255 or watchdog shutdown:
  it may already have run. `--tmux` is exempt because attaching the named session
  is safe to repeat. Run work inside that session if it must survive a drop.
- Fatal host-key/configuration errors stop recovery. The wrapper does not repair
  `known_hosts`, refresh credentials, log into portals, or change VPN settings.
- Private masters deliberately give up connection sharing across `ssa`
  invocations. Each new invocation and reconnect pays the connection setup cost.
- Shutdown controls the SSH child and heartbeat process groups. Arbitrary
  detached proxy descendants are not guaranteed to be terminated.

The classifier reads the final three nonempty stderr lines. It can explain common
SSH/SSM failures, but stderr is shared with remote programs and is not a protocol
for determining whether a command ran. Authentication diagnostics may inspect
`~/.ssh/id_rsa-cert.pub` with `ssh-keygen`. Connection failures may be refined by
a bounded captive-portal check using `curl`.

## Existing solutions

[OpenSSH keepalives](https://man.openbsd.org/ssh_config#ServerAliveInterval) detect
an unresponsive encrypted transport. With interval 15 and count 3, the documented
disconnect time is approximately 45 seconds. A supervisor is needed to reconnect
after SSH exits.

[autossh](https://www.harding.motd.ca/autossh/) is the established supervisor.
Its port monitor sends traffic through a forwarding loop on the supervised
connection. `-M 0` disables that monitor and relies on SSH exiting; the
[autossh manual](https://raw.githubusercontent.com/Autossh/autossh/master/autossh.1)
explicitly recommends native SSH keepalives for many uses. It is a reasonable
choice for tunnels or when its retry and exit behavior meets your needs. `ssa`
adds the tmux convenience, failure explanations, command replay guard, and a
channel heartbeat without requiring a monitor port.

[mosh](https://github.com/mobile-shell/mosh) keeps a roaming terminal session
across sleep and address changes. It requires `mosh-server` and UDP connectivity
after SSH startup. A normal SSM ProxyCommand byte stream alone does not provide
that UDP path, and mosh is not a replacement for SSH forwarding or arbitrary
remote commands.

The key OpenSSH detail is that
[`ControlMaster=no`](https://man.openbsd.org/ssh_config#ControlMaster) still permits
using a configured master, and a failed multiplexing attempt can fall back to a
fresh connection. `ssh -O check` only checks the local master process. Neither is
sufficient evidence that the original remote transport works.

## Verification

```sh
./test_ssa.py
./mutants.sh
SSA_TEST_SSHD=/usr/sbin/sshd python3 -m unittest -v test_ssh
```

`test_ssa.py` covers classification, retries, signal handling, hung subprocesses,
closed/noisy stderr, suspend detection, command replay, and real pseudo-terminals
using local process stubs.

`test_ssh.py` is an opt-in suite using the installed OpenSSH client and an
unprivileged `sshd` over local pipes, with disposable keys. No network port
listens, and no user SSH files are read or changed. It freezes the original server
while a fresh connection succeeds, removes a live master's listening socket,
rejects new proxy authentication, and checks that the supervisor reconnects.
Some sandboxes deny the system sshd's audit operations.

`mutants.sh` deliberately breaks selected behaviors in temporary copies and checks
that the corresponding tests fail. It leaves the working source untouched.
Setting `SSA_TEST_SSHD` also enables a real SSH fallback mutation.
These tests validate the exercised cases; they do not prove recovery from every
operating-system, network, or remote-application failure.
