#!/usr/bin/env python3
"""Checks for ssa.

Three kinds, in increasing order of cost:

- **pure** -- import ssa and call it. The classifier, the CLI and the width
  budget are decided by data, so they are checked by reading that data rather
  than by sampling a run.
- **process** -- drive the real executable against a stub ssh, which is what
  makes the interesting cases reachable: a changed host key, an expired
  certificate, a live control master behind expired proxy credentials, a probe
  that never returns, a descendant that keeps stderr open after ssh has gone.
- **pty** -- allocate a terminal, because ownership of it and the keypress
  window cannot be observed without one.

Every check here is a failure that happened, or a promise the README makes. No
check asserts the shape of the repository.

Usage: ./test_ssa.py [-v]
"""

from __future__ import annotations

import importlib.util
import os
import pty
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import termios
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SSA = HERE / "ssa"


def _load():
    spec = importlib.util.spec_from_loader(
        "ssa_module", importlib.machinery.SourceFileLoader("ssa_module", str(SSA))
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["ssa_module"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ssa = _load()

STUB = r"""#!/usr/bin/env python3
import os, signal, sys, time

argv = " ".join(sys.argv[1:])
if " -G " in f" {argv} ":
    print("hostname testhost")
    print("port 22")
    print("user tester")
    print(f"serveraliveinterval {os.environ.get('STUB_ALIVE', '60')}")
    if os.environ.get("STUB_ADVERTISE"):
        print("remotecommand none")
        print("sessiontype default")
    sys.exit(0)

count = os.environ["STUB_COUNT"]
n = 1 + (int(open(count).read().strip() or 0) if os.path.exists(count) else 0)
open(count, "w").write(str(n))
tty = "tty" if os.isatty(0) else "notty"
with open(os.environ["STUB_LOG"], "a") as log:
    log.write(f"{n}\t{argv}\t{tty}\n")

# A control-socket call is not a session, so it does not consume a plan step:
# ssa makes one before every wait, and counting them would shift every plan.
if " -O " in f" {argv} ":
    if os.environ.get("STUB_DELAY_CTL"):
        time.sleep(float(os.environ["STUB_DELAY_CTL"]))
    sys.exit(0 if os.environ.get("STUB_MUX_LIVE") else 1)

if os.environ.get("STUB_DELAY_PROBE") and "ConnectTimeout=" in argv:
    time.sleep(float(os.environ["STUB_DELAY_PROBE"]))

# A ProxyCommand descendant outliving ssh with fd 2 still open, so the parent's
# stderr pipe never reaches EOF. Nothing signals it: a grandchild is not ssa's.
if os.environ.get("STUB_ORPHAN"):
    if os.fork() == 0:
        os.setsid()
        time.sleep(float(os.environ["STUB_ORPHAN"]))
        os._exit(0)

if os.environ.get("STUB_HOLD"):
    # Record a TERM we were able to *handle*: a stopped process has TERM left
    # pending, so this file exists only if something resumed us first. Without
    # it, the wrapper's kill fallback ends us and ssh never restores the tty.
    def _termed(_signum, _frame):
        open(os.environ["STUB_HOLD"] + ".termed", "w").write("termed")
        os._exit(143)

    signal.signal(signal.SIGTERM, _termed)
    open(os.environ["STUB_HOLD"], "w").write(str(os.getpid()))
    time.sleep(60)
    sys.exit(0)

# A session on a link that died: ssh never exits on its own, because its
# keepalive is defeated (a master with stale values, or a suspend). Probes are
# exempt -- they answer from the plan -- and a *second* session falls through,
# so a reconnect after the watchdog's kill can be observed. The TERM handler
# records that the watchdog, not a fallback kill, ended the session.
hold = os.environ.get("STUB_HOLD_SESSION")
if hold and "ConnectTimeout=" not in argv and not os.path.exists(hold + ".termed"):
    def _watch_termed(_signum, _frame):
        open(hold + ".termed", "w").write("termed")
        os._exit(143)

    signal.signal(signal.SIGTERM, _watch_termed)
    open(hold, "w").write(str(os.getpid()))
    time.sleep(float(os.environ.get("STUB_HOLD_FOR", "60")))
    sys.exit(0)

# A live ControlMaster reached through a ProxyCommand whose credentials have
# expired: the socket answers, and only a fresh handshake pays for credentials.
if os.environ.get("STUB_MUX_LIVE") and "ControlPath=none" in argv:
    print("An error occurred (ExpiredTokenException) when calling StartSession", file=sys.stderr)
    print("ssh_exchange_identification: Connection closed by remote host", file=sys.stderr)
    sys.exit(255)

plan = os.environ["STUB_PLAN"].split(";")
sessions = os.environ["STUB_COUNT"] + ".sessions"
i = 1 + (int(open(sessions).read().strip() or 0) if os.path.exists(sessions) else 0)
open(sessions, "w").write(str(i))
step = plan[i - 1] if i - 1 < len(plan) else plan[-1]
rc, _, msg = step.partition(":")
if msg:
    print(msg.replace("\\n", "\n"), file=sys.stderr)
sys.exit(int(rc))
"""

CURL = """#!/usr/bin/env python3
import os, sys
sys.stdout.write(os.environ.get("STUB_PORTAL_CODE", "204"))
"""

KEYGEN = """#!/usr/bin/env python3
import os, sys
path = sys.argv[-1]
if not os.path.exists(path):
    sys.exit(1)
to = os.environ.get("STUB_CERT_TO", "2030-01-01T00:00:00")
print(f"        Valid: from 2020-01-01T00:00:00 to {to}")
"""


class Harness(unittest.TestCase):
    """A scratch HOME and a stub ssh on PATH, so no check touches the network."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ssa-test."))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        bin_ = self.tmp / "bin"
        bin_.mkdir()
        for name, body in (("ssh", STUB), ("curl", CURL), ("ssh-keygen", KEYGEN)):
            path = bin_ / name
            path.write_text(body)
            path.chmod(0o755)
        (self.tmp / ".ssh").mkdir()
        self.log = self.tmp / "log"
        self.count = self.tmp / "count"
        self.env = {
            **os.environ,
            "PATH": f"{bin_}:{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "STUB_LOG": str(self.log),
            "STUB_COUNT": str(self.count),
            "STUB_ALIVE": "60",
        }

    def run_ssa(self, *args: str, timeout: float = 60, **env: str):
        return subprocess.run(
            [sys.executable, str(SSA), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            stdin=subprocess.DEVNULL,
            env={**self.env, **env},
        )

    def calls(self) -> list[str]:
        if not self.log.exists():
            return []
        return [
            line.split("\t")[1] for line in self.log.read_text().splitlines() if line.strip()
        ]

    def probes(self) -> list[str]:
        return [call for call in self.calls() if "ConnectTimeout=" in call]


class Classifier(unittest.TestCase):
    """The table is data, so these read it rather than sampling behaviour."""

    def test_every_row_is_a_known_class_and_three_fields(self) -> None:
        for rule in ssa.RULES:
            self.assertIsInstance(rule.cls, ssa.Class)
            self.assertTrue(rule.reason and rule.pattern)

    def test_no_pattern_appears_twice(self) -> None:
        patterns = [rule.pattern for rule in ssa.RULES]
        self.assertCountEqual(patterns, set(patterns))

    def test_every_row_reaches_the_terminal_as_written(self) -> None:
        for rule in ssa.RULES:
            why = ssa.diagnose(f"ssh: {rule.pattern} happened")
            self.assertEqual(rule.cls, why.cls)
            self.assertEqual(rule.reason, why.reason)

    def test_every_reason_fits_the_width_budget(self) -> None:
        for rule in ssa.RULES:
            line = f"{ssa.PROG}: waiting for {'h' * 20}: {rule.reason}"
            self.assertLessEqual(len(line), 80, rule.reason)
        for wording in (ssa.NO_DIAGNOSTIC, ssa.WEDGED):
            line = f"{ssa.PROG}: waiting for {'h' * 20}: {wording}"
            self.assertLessEqual(len(line), 80, wording)

    def test_the_cap_on_ssh_wording_matches_that_bound(self) -> None:
        widest = f"{ssa.PROG}: waiting for {'h' * 20}: {'r' * ssa.REASON_MAX}"
        self.assertEqual(80, len(widest))

    def test_unclassified_stderr_is_capped_to_that_bound(self) -> None:
        why = ssa.diagnose("ssh: " + "x" * 200)
        self.assertIs(ssa.Class.DROPPED, why.cls)
        self.assertLessEqual(len(why.reason), ssa.REASON_MAX)

    def test_a_silent_drop_says_so(self) -> None:
        self.assertEqual(ssa.NO_DIAGNOSTIC, ssa.diagnose("").reason)

    def test_a_proxy_diagnostic_outranks_the_handshake_line_under_it(self) -> None:
        why = ssa.diagnose(
            "An error occurred (ExpiredTokenException) when calling StartSession\n"
            "ssh_exchange_identification: Connection closed by remote host\n"
        )
        self.assertIs(ssa.Class.AUTH, why.cls)
        self.assertEqual("proxy credentials expired", why.reason)

    def test_a_line_from_an_attempt_that_recovered_is_not_the_reason(self) -> None:
        why = ssa.diagnose(
            "ssh: connect to host h port 22: Connection refused\n"
            + "\n".join(f"noise {i}" for i in range(ssa.TAIL_LINES))
            + "\nConnection to h closed by remote host.\n"
        )
        self.assertIs(ssa.Class.DROPPED, why.cls)

    def test_a_tty_carriage_return_does_not_reach_the_status_line(self) -> None:
        self.assertNotIn("\r", ssa.diagnose("Connection to h closed.\r\n").reason)

    def test_a_cert_expiry_does_not_defeat_the_print_cadence(self) -> None:
        first = ssa.diagnose("Permission denied", lambda: "cert expired 1m00s ago")
        later = ssa.diagnose("Permission denied", lambda: "cert expired 9m00s ago")
        self.assertNotEqual(first.reason, later.reason)
        self.assertEqual(first.key, later.key)

    def test_the_cert_note_is_not_attached_to_every_rejection(self) -> None:
        why = ssa.diagnose("Too many authentication failures", lambda: "cert expired 1m00s ago")
        self.assertEqual("too many authentication attempts", why.reason)

    def test_an_unreadable_cert_is_not_reported_as_expired(self) -> None:
        self.assertIsNone(ssa.cert_expiry(None, 0.0, lambda _: None))
        self.assertIsNone(ssa.cert_expiry("", 0.0, lambda _: None))

    def test_a_live_cert_is_ruled_out_explicitly(self) -> None:
        note = ssa.cert_expiry("2030-01-01T00:00:00", 0.0, lambda _: 1.0e12)
        self.assertEqual("credentials rejected, cert is live", note)

    def test_an_overnight_duration_reads_in_hours(self) -> None:
        self.assertEqual("30s", ssa.duration(30))
        self.assertEqual("2m30s", ssa.duration(150))
        self.assertEqual("10h55m", ssa.duration(39300))


class Interface(unittest.TestCase):
    def test_a_host_is_enough(self) -> None:
        self.assertEqual("h", ssa.parse(["h"]).host)
        self.assertEqual((), ssa.parse(["h"]).command)

    def test_a_remote_command_is_kept_whole(self) -> None:
        options = ssa.parse(["h", "echo", "a b", "*"])
        self.assertEqual(("echo", "a b", "*"), options.command)

    def test_a_flag_after_the_host_belongs_to_the_remote_command(self) -> None:
        self.assertEqual(("ls", "-l"), ssa.parse(["h", "ls", "-l"]).command)

    def test_an_ssh_flag_is_refused_naming_where_it_goes(self) -> None:
        with self.assertRaises(ssa.Refused) as refused:
            ssa.parse(["-f", "h"])
        self.assertIn("-f", str(refused.exception))
        self.assertIn("~/.ssh/config", str(refused.exception))

    def test_an_unknown_long_option_is_refused(self) -> None:
        with self.assertRaises(ssa.Refused):
            ssa.parse(["--nope", "h"])

    def test_help_is_not_a_refusal(self) -> None:
        with self.assertRaises(ssa.Helped):
            ssa.parse(["--help"])

    def test_a_host_that_looks_like_a_session_name_is_still_the_host(self) -> None:
        """`--tmux` must not eat the next token, or the host becomes the name."""
        options = ssa.parse(["--tmux", "gpu2"])
        self.assertEqual("gpu2", options.host)
        self.assertEqual("main", options.tmux)

    def test_tmux_defaults_and_names_a_session(self) -> None:
        self.assertEqual("main", ssa.parse(["--tmux", "h"]).tmux)
        self.assertEqual("build", ssa.parse(["--tmux=build", "h"]).tmux)

    def test_tmux_plus_a_command_is_refused(self) -> None:
        with self.assertRaises(ssa.Refused) as refused:
            ssa.parse(["--tmux", "h", "uptime"])
        self.assertIn("--tmux=NAME", str(refused.exception))

    def test_no_host_is_refused(self) -> None:
        with self.assertRaises(ssa.Refused):
            ssa.parse([])

    def test_the_tmux_command_attaches_or_creates_in_utf8(self) -> None:
        remote = ssa.parse(["--tmux=w", "h"]).remote
        self.assertEqual(("tmux", "-u", "new", "-A", "-s", "w"), remote)

    def test_the_host_is_named_by_its_first_label(self) -> None:
        self.assertEqual("dev", ssa.parse(["dev.example.com"]).label)

    def test_the_session_cannot_prompt(self) -> None:
        argv = ssa.Session(ssa.parse(["h"])).argv()
        self.assertEqual(["ssh", "-o", "BatchMode=yes", "h"], argv)

    def test_tmux_forces_a_terminal(self) -> None:
        self.assertIn("-t", ssa.Session(ssa.parse(["--tmux", "h"])).argv())

    def test_the_probe_adds_only_options_that_bound_the_attempt(self) -> None:
        # Read the argv the probe would use, without connecting.
        ssh = ssa.Ssh("h")
        with mock.patch.object(ssh, "_bounded", return_value=(0, "")) as bounded:
            ssh.probe()
        argv = bounded.call_args.args[0]
        self.assertEqual("ssh", argv[0])
        self.assertEqual(["h", "true"], argv[-2:])
        allowed = {
            "BatchMode=yes",
            f"ConnectTimeout={ssa.PROBE_CONNECT}",
            "ControlMaster=no",
            "ClearAllForwardings=yes",
        }
        for value in [a for i, a in enumerate(argv) if i and argv[i - 1] == "-o"]:
            self.assertIn(value, allowed)
        self.assertNotIn("ControlPath", " ".join(argv))

    def test_an_older_client_is_not_sent_options_it_rejects(self) -> None:
        self.assertEqual((), ssa.probe_resets("hostname h\nport 22\n"))

    def test_a_newer_client_has_what_would_suppress_its_command_reset(self) -> None:
        resets = ssa.probe_resets("remotecommand none\nsessiontype default\n")
        self.assertEqual(("-o", "RemoteCommand=none", "-o", "SessionType=default"), resets)

    def test_the_keepalive_refusal_names_the_host_not_a_wildcard(self) -> None:
        text = ssa.keepalive_refusal("gpu2")
        self.assertIn("Host gpu2", text)
        self.assertNotIn("Host *", text)

    def test_a_portal_is_reported_only_when_it_answers(self) -> None:
        self.assertIsNone(ssa.portal(lambda _: (0, "204")))
        self.assertIsNone(ssa.portal(lambda _: (0, "000")))
        self.assertIn("HTTP 302", ssa.portal(lambda _: (0, "302")) or "")


class Cadence(unittest.TestCase):
    """One line on entry, one per change of reason, else one per NOTE_EVERY."""

    class Stream:
        def __init__(self) -> None:
            self.lines: list[str] = []

        def write(self, text: str) -> int:
            if text.strip():
                self.lines.append(text.strip())
            return len(text)

        def flush(self) -> None:
            pass

    def report(self, now: list[float]) -> tuple[ssa.Reporter, Stream]:
        stream = self.Stream()
        return ssa.Reporter(clock=lambda: now[0], stream=stream), stream

    def test_a_steady_reason_is_not_reprinted_per_probe(self) -> None:
        now = [0.0]
        report, stream = self.report(now)
        why = ssa.Diagnosis.of(ssa.Class.CONNECT, "connection refused")
        report.waiting("h", why)
        for _ in range(20):
            now[0] += 5
            report.still(now[0], why)
        self.assertEqual(1, len(stream.lines))

    def test_a_keepalive_line_arrives_once_per_note_every(self) -> None:
        now = [0.0]
        report, stream = self.report(now)
        why = ssa.Diagnosis.of(ssa.Class.CONNECT, "connection refused")
        report.waiting("h", why)
        now[0] += ssa.NOTE_EVERY
        report.still(now[0], why)
        self.assertEqual(2, len(stream.lines))

    def test_a_changed_reason_is_reported_once(self) -> None:
        now = [0.0]
        report, stream = self.report(now)
        report.waiting("h", ssa.Diagnosis.of(ssa.Class.CONNECT, "unresolved host"))
        changed = ssa.Diagnosis.of(ssa.Class.CONNECT, "connection refused")
        now[0] += 1
        report.still(now[0], changed)
        now[0] += 1
        report.still(now[0], changed)
        self.assertEqual(2, len(stream.lines))

    def test_a_ticking_duration_does_not_defeat_the_cadence(self) -> None:
        now = [0.0]
        report, stream = self.report(now)
        report.waiting(
            "h", ssa.Diagnosis(ssa.Class.AUTH, "cert expired 1m00s ago", "credentials rejected")
        )
        for minute in range(2, 6):
            now[0] += 60
            report.still(
                now[0],
                ssa.Diagnosis(
                    ssa.Class.AUTH, f"cert expired {minute}m00s ago", "credentials rejected"
                ),
            )
        self.assertEqual(1, len(stream.lines))

    def test_no_line_exceeds_80_columns_at_its_worst_case(self) -> None:
        now = [0.0]
        report, stream = self.report(now)
        why = ssa.Diagnosis.of(ssa.Class.DROPPED, "r" * ssa.REASON_MAX)
        report.waiting("h" * 20, why)
        now[0] += ssa.NOTE_EVERY
        report.still(39300, why)
        report.back("h" * 20, 39300)
        report.say(f"link dead: {'r' * ssa.REASON_MAX}")
        for line in stream.lines:
            self.assertLessEqual(len(line), 80, line)


class Behaviour(Harness):
    """Drive the real executable; the network is a stub."""

    def test_a_clean_exit_is_zero_and_does_not_reconnect(self) -> None:
        done = self.run_ssa("host", STUB_PLAN="0:")
        self.assertEqual(0, done.returncode)
        self.assertEqual(1, len(self.calls()))

    def test_a_remote_status_passes_through(self) -> None:
        self.assertEqual(3, self.run_ssa("host", "true", STUB_PLAN="3:").returncode)

    def test_a_dropped_remote_command_runs_once_and_says_why(self) -> None:
        done = self.run_ssa("host", "make", "deploy", STUB_PLAN="255:Connection closed.;0:")
        self.assertEqual(255, done.returncode)
        self.assertEqual(1, len(self.calls()))
        self.assertIn("--tmux", done.stderr)

    def test_a_changed_host_key_stops_naming_the_ambiguity(self) -> None:
        done = self.run_ssa(
            "host", STUB_PLAN="255:@@@ WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED @@@"
        )
        self.assertEqual(255, done.returncode)
        self.assertEqual(1, len(self.calls()))
        self.assertIn("host key changed", done.stderr)
        self.assertIn("MITM", done.stderr)

    def test_an_interactive_drop_reconnects(self) -> None:
        done = self.run_ssa(
            "host", STUB_PLAN="255:Connection to host closed by remote host.;0:;0:"
        )
        self.assertEqual(0, done.returncode)
        self.assertIn("waiting for host", done.stderr)
        self.assertIn("back after", done.stderr)
        self.assertGreaterEqual(len(self.probes()), 1)

    def test_no_ssh_flag_ever_reaches_ssh(self) -> None:
        done = self.run_ssa("-f", "host", STUB_PLAN="0:")
        self.assertEqual(255, done.returncode)
        self.assertEqual([], self.calls())
        self.assertIn("~/.ssh/config", done.stderr)

    def test_a_missing_keepalive_is_refused_before_connecting(self) -> None:
        done = self.run_ssa("host", STUB_PLAN="0:", STUB_ALIVE="0")
        self.assertEqual(255, done.returncode)
        self.assertEqual([], self.calls())
        self.assertIn("ServerAliveInterval", done.stderr)
        self.assertIn("Host host", done.stderr)

    def test_a_configured_keepalive_connects_untouched(self) -> None:
        self.assertEqual(0, self.run_ssa("host", STUB_PLAN="0:", STUB_ALIVE="15").returncode)

    def test_rejected_credentials_wait_rather_than_prompt(self) -> None:
        done = self.run_ssa("host", STUB_PLAN="255:Permission denied (publickey).;0:;0:")
        self.assertEqual(0, done.returncode)
        self.assertIn("credentials rejected", done.stderr)

    def test_an_expired_cert_explains_the_rejection(self) -> None:
        (self.tmp / ".ssh" / "id_rsa-cert.pub").write_text("cert")
        done = self.run_ssa(
            "host",
            STUB_PLAN="255:Permission denied (publickey).;0:;0:",
            STUB_CERT_TO="2020-01-02T00:00:00",
        )
        self.assertEqual(0, done.returncode)
        self.assertIn("cert expired", done.stderr)

    def test_a_probe_reaches_a_live_control_master(self) -> None:
        done = self.run_ssa(
            "host",
            STUB_PLAN="255:Connection to host closed by remote host.;0:;0:",
            STUB_MUX_LIVE="1",
        )
        self.assertEqual(0, done.returncode)
        self.assertNotIn("ControlPath=none", " ".join(self.calls()))

    def test_the_stale_master_check_precedes_the_first_probe(self) -> None:
        self.run_ssa("host", STUB_PLAN="255:Connection closed by remote host.;0:;0:")
        calls = self.calls()
        control = next(i for i, call in enumerate(calls) if " -O " in f" {call} ")
        probe = next(i for i, call in enumerate(calls) if "ConnectTimeout=" in call)
        self.assertLess(control, probe)

    def test_a_portal_refines_a_connection_failure(self) -> None:
        """A portal only refines a probe that *failed*, hence two refusals."""
        refused = "255:ssh: connect to host h port 22: Connection refused"
        done = self.run_ssa(
            "host",
            STUB_PLAN=f"{refused};{refused};0:",
            STUB_PORTAL_CODE="302",
        )
        self.assertIn("captive portal", done.stderr)

    def test_a_probe_that_will_not_return_is_cut_off(self) -> None:
        """PROBE_WALL, not ConnectTimeout, is what bounds a wedged probe."""
        start = time.monotonic()
        done = subprocess.run(
            [sys.executable, "-c", _bounded_probe_driver(), str(SSA)],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
            env={**self.env, "STUB_DELAY_PROBE": "60", "STUB_PLAN": "255:Connection closed.;0:"},
        )
        self.assertEqual("cut-off", done.stdout.strip(), done.stderr)
        self.assertLess(time.monotonic() - start, 80)

    def test_a_descendant_holding_stderr_does_not_delay_the_diagnosis(self) -> None:
        """The wrapper must not wait on a grandchild that outlives ssh.

        ssa's stderr goes to a file, not a pipe: the orphan inherits whatever we
        give ssa, so capturing through a pipe would time the harness's own drain
        rather than ssa -- which is how this check first read as a 46s failure
        against a wrapper that had already finished.
        """
        out = self.tmp / "out"
        start = time.monotonic()
        with out.open("wb") as sink:
            proc = subprocess.Popen(
                [sys.executable, str(SSA), "host"],
                stdin=subprocess.DEVNULL,
                stdout=sink,
                stderr=sink,
                env={
                    **self.env,
                    "STUB_ORPHAN": "45",
                    "STUB_PLAN": "255:Connection to host closed by remote host.;0:",
                },
            )
            self.assertEqual(0, proc.wait(timeout=40))
        self.assertLess(time.monotonic() - start, 40)
        self.assertIn("back after", out.read_text())

    def test_term_stops_the_session_and_exits_143(self) -> None:
        proc, child = self._held_session()
        proc.send_signal(signal.SIGTERM)
        self.assertEqual(143, proc.wait(timeout=30))
        self.assertFalse(_alive(child), "the ssh child outlived the wrapper")

    def test_a_stopped_session_is_resumed_so_term_can_reach_it(self) -> None:
        """A suspended child never reaps: SIGCONT has to precede SIGTERM.

        This is the shape that wedges a terminal in practice -- tmux's
        suspend-client, or ~^Z -- where the session is stopped and the wrapper is
        then asked to stop. The child must *handle* the TERM, because that is
        where ssh restores the terminal; being killed while stopped is what
        leaves the tty raw. So the assertion is on graceful handling, not merely
        on the pid being gone -- the kill fallback would satisfy that either way.
        """
        proc, child = self._held_session()
        os.kill(child, signal.SIGSTOP)
        _await_state(child, "T")
        proc.send_signal(signal.SIGTERM)
        self.assertEqual(143, proc.wait(timeout=30))
        self.assertFalse(_alive(child), "a stopped ssh child outlived the wrapper")
        self.assertTrue(
            (self.tmp / "hold.termed").exists(),
            "the stopped child was killed rather than resumed and asked to stop",
        )

    def _held_session(self):
        hold = self.tmp / "hold"
        proc = subprocess.Popen(
            [sys.executable, str(SSA), "host"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**self.env, "STUB_HOLD": str(hold), "STUB_PLAN": "0:"},
        )
        self.addCleanup(_reap, proc)
        return proc, _await_pid(hold)


class Watch(Harness):
    """T14: a dead link is noticed by ssa itself, while the session is up.

    These drive Session and Supervisor in-process so the cadence constants can
    be patched down; the ssh, the probes and the kill are all real processes.
    The stub's held session is a link that died under ssh with its keepalive
    defeated -- it never exits on its own, which is exactly the frozen screen.
    """

    REFUSED = "255:ssh: connect to host h port 22: Connection refused"

    def _run(self, plan: str, wall=None, every: float = 0.2, hold: str = "8.0"):
        options = ssa.parse(["host"])
        watch = ssa.Watchdog(ssh=ssa.Ssh("host"), **({"wall": wall} if wall else {}))
        session = ssa.Session(options, watch=watch)
        env = {
            **self.env,
            "STUB_PLAN": plan,
            "STUB_HOLD_SESSION": str(self.tmp / "hold"),
            "STUB_HOLD_FOR": hold,
        }
        with mock.patch.dict(os.environ, env), mock.patch.object(ssa, "WATCH_EVERY", every):
            status, _ = session.run()
        return session, status

    def test_a_dead_link_is_noticed_and_the_session_dropped(self) -> None:
        session, _ = self._run(f"{self.REFUSED};{self.REFUSED}")
        self.assertIsNotNone(session.why, "the watchdog never declared the link dead")
        self.assertIs(ssa.Class.CONNECT, session.why.cls)
        self.assertTrue(
            (self.tmp / "hold.termed").exists(),
            "the session was killed rather than asked to stop",
        )

    def test_an_auth_refusal_never_drops_a_live_session(self) -> None:
        """A cert expiring mid-session is daily, and proves the path is up."""
        session, status = self._run("255:Permission denied (publickey).", hold="2.0")
        self.assertIsNone(session.why)
        self.assertEqual(0, status)
        self.assertGreaterEqual(len(self.probes()), 2, "the probes never ran")

    def test_one_wedged_probe_is_not_a_dead_link(self) -> None:
        """The far end paging can wedge one probe; the second one is the link."""
        session, status = self._run(f"{self.REFUSED};0:", hold="2.0")
        self.assertIsNone(session.why)
        self.assertEqual(0, status)

    def test_a_resume_probes_at_once_instead_of_on_the_cadence(self) -> None:
        """Monotonic clocks stop during a suspend, and so does ssh's keepalive
        schedule; the wall clock outrunning them is the wake ssa acts on."""
        ticks = {"n": 0}

        def wall() -> float:
            ticks["n"] += 1
            return time.time() + (ssa.RESUME_JUMP + 5 if ticks["n"] > 5 else 0.0)

        session, _ = self._run("0:", wall=wall, every=60.0, hold="2.0")
        self.assertIsNone(session.why)
        self.assertGreaterEqual(len(self.probes()), 1, "no probe followed the resume")

    def test_a_watchdog_kill_reconnects_without_a_grace_window(self) -> None:
        """End to end: kill, report, wait, reconnect -- and the kill's status is
        never mistaken for the remote command's (T4)."""
        stream = Cadence.Stream()
        options = ssa.parse(["host"])
        supervisor = ssa.Supervisor(
            options=options,
            ssh=ssa.Ssh("host"),
            report=ssa.Reporter(stream=stream),
            delays=[0.05] * 50,
        )
        env = {
            **self.env,
            "STUB_PLAN": f"{self.REFUSED};{self.REFUSED};0:;0:",
            "STUB_HOLD_SESSION": str(self.tmp / "hold"),
            "STUB_HOLD_FOR": "8.0",
        }
        with mock.patch.dict(os.environ, env), mock.patch.object(ssa, "WATCH_EVERY", 0.2):
            status = supervisor.run()
        self.assertEqual(0, status)
        text = "\n".join(stream.lines)
        self.assertIn("link dead: connection refused", text)
        self.assertIn("waiting for host", text)
        self.assertIn("back after", text)


def _bounded_probe_driver() -> str:
    """Watch a wait whose probes never answer, and report that it kept going.

    A bound is a claim about the clock, so the only way to check it is to point
    ssa at something that will not come back. It asserts that the loop ran
    again, not an exact duration, so a loaded machine does not read as a defect.
    """
    return textwrap.dedent(
        """
        import os, subprocess, sys, time
        ssa = sys.argv[1]
        proc = subprocess.Popen(
            [sys.executable, ssa, "host"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=os.environ.copy(),
        )
        log = os.environ["STUB_LOG"]
        deadline = time.time() + 60
        seen = 0
        while time.time() < deadline:
            if os.path.exists(log):
                seen = sum("ConnectTimeout=" in l for l in open(log))
            if seen >= 2:
                break
            time.sleep(0.5)
        proc.terminate()
        proc.wait(timeout=30)
        print("cut-off" if seen >= 2 else f"wedged after {seen} probe(s)")
        """
    )


def _await_pid(path, timeout: float = 30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists() and path.read_text().strip():
            return int(path.read_text().strip())
        time.sleep(0.05)
    raise AssertionError(f"{path} never held a pid")


def _await_state(pid: int, state: str, timeout: float = 10) -> None:
    """Wait for a kernel process state, so the check does not race the signal."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        stat = Path(f"/proc/{pid}/stat").read_text()
        if stat[stat.rfind(")") + 2 :].split()[0] == state:
            return
        time.sleep(0.05)
    raise AssertionError(f"pid {pid} never reached state {state}")


def _reap(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.kill()
        proc.wait(timeout=10)


def _alive(pid: int) -> bool:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGCONT)
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    return True


class Terminal(Harness):
    """Ownership of the terminal and the keypress window need a real pty."""

    def under_pty(self, keys: bytes, timeout: float = 45, **env: str) -> tuple[int, str]:
        pid, fd = pty.fork()
        if pid == 0:
            os.environ.update({**self.env, **env})
            os.execv(sys.executable, [sys.executable, str(SSA), "host"])
        try:
            time.sleep(0.7)
            if keys:
                os.write(fd, keys)
            out = b""
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    if select.select([fd], [], [], 0.5)[0]:
                        chunk = os.read(fd, 65536)
                        if not chunk:
                            break
                        out += chunk
                except OSError:
                    break
                done, status = os.waitpid(pid, os.WNOHANG)
                if done:
                    return os.waitstatus_to_exitcode(status), out.decode(errors="replace")
            return os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1]), out.decode(errors="replace")
        finally:
            try:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass
            os.close(fd)

    def test_the_session_inherits_the_terminal(self) -> None:
        status, _ = self.under_pty(b"", STUB_PLAN="0:")
        self.assertEqual(0, status)
        self.assertIn("tty", self.log.read_text())

    def test_a_queued_escape_sequence_does_not_abort_the_reconnect(self) -> None:
        status, out = self.under_pty(
            b"\x1b[<0;1;1M", STUB_PLAN="255:Connection to host closed by remote host.;0:;0:"
        )
        self.assertEqual(0, status, out)

    def test_q_stops_the_reconnect(self) -> None:
        status, out = self.under_pty(
            b"q", STUB_PLAN="255:Connection to host closed by remote host.;0:;0:"
        )
        self.assertEqual(255, status, out)

    def test_the_terminal_is_restored_after_the_keypress_window(self) -> None:
        """cbreak left on would eat the next shell's line editing."""
        pid, fd = pty.fork()
        if pid == 0:
            os.environ.update(
                {**self.env, "STUB_PLAN": "255:Connection to host closed by remote host.;0:;0:"}
            )
            os.execv(sys.executable, [sys.executable, str(SSA), "host"])
        try:
            before = termios.tcgetattr(fd)
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if select.select([fd], [], [], 0.5)[0]:
                    try:
                        if not os.read(fd, 65536):
                            break
                    except OSError:
                        break
                if os.waitpid(pid, os.WNOHANG)[0]:
                    break
            self.assertEqual(before[3], termios.tcgetattr(fd)[3])
        finally:
            try:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass
            os.close(fd)


if __name__ == "__main__":
    unittest.main(verbosity=2)
