"""Opt-in tests using real OpenSSH over local pipes, with disposable keys.

SSA_TEST_SSHD=/usr/sbin/sshd python3 -m unittest -v test_ssh

Nothing listens on a network port, and no user SSH files are read or changed.
The server runs as the caller; environments that restrict sshd's audit support
may require running these tests outside their sandbox.
"""

from __future__ import annotations

import json
import os
import pwd
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from test_ssa import HERE, ssa

SSHD = os.environ.get("SSA_TEST_SSHD")
SSH = shutil.which("ssh")
KEYGEN = shutil.which("ssh-keygen")
HOST = "ssa-local-test"


@unittest.skipUnless(SSHD and SSH and KEYGEN, "set SSA_TEST_SSHD to enable local OpenSSH tests")
class OpenSSH(unittest.TestCase):
    def setUp(self) -> None:
        if os.getuid() == 0:
            self.skipTest("run the disposable SSH server as an unprivileged user")
        self.tmp = Path(tempfile.mkdtemp(prefix="ssa-openssh-", dir="/tmp"))
        self.children: list[subprocess.Popen] = []
        self.streams = []
        self.addCleanup(self.cleanup)
        self.server_pids = self.tmp / "servers"
        self.calls = self.tmp / "calls"
        self.denied = self.tmp / "reject-new-connections"
        for key in ("host", "user"):
            subprocess.run(
                [KEYGEN, "-q", "-t", "rsa", "-b", "2048", "-N", "", "-f", str(self.tmp / key)],
                check=True, stdin=subprocess.DEVNULL, capture_output=True, timeout=15,
            )
        authorized = self.tmp / "authorized_keys"
        authorized.write_text((self.tmp / "user.pub").read_text())
        authorized.chmod(0o600)
        (self.tmp / "known_hosts").write_text(
            f"{HOST} " + (self.tmp / "host.pub").read_text()
        )
        server_config = self.tmp / "sshd_config"
        server_config.write_text(
            f'HostKey "{self.tmp / "host"}"\n'
            f'PidFile "{self.tmp / "sshd.pid"}"\n'
            f'AuthorizedKeysFile "{authorized}"\n'
            "StrictModes no\nPasswordAuthentication no\n"
            "ChallengeResponseAuthentication no\nUsePAM no\n"
            "UsePrivilegeSeparation no\nLogLevel ERROR\n"
        )
        proxy = self.tmp / "proxy.py"
        proxy.write_text(
            "import os, sys\n"
            "from pathlib import Path\n"
            f"if Path({str(self.denied)!r}).exists():\n"
            "    print('ExpiredToken: test proxy credentials expired', file=sys.stderr)\n"
            "    sys.exit(1)\n"
            f"with open({str(self.server_pids)!r}, 'a') as out:\n"
            "    out.write(str(os.getpid()) + '\\n')\n"
            f"os.execv({SSHD!r}, [{SSHD!r}, '-i', '-e', '-f', {str(server_config)!r}])\n"
        )
        self.config = self.tmp / "ssh_config"
        self.config.write_text(
            f"Host {HOST}\n"
            f"  HostName {HOST}\n"
            f"  User {pwd.getpwuid(os.getuid()).pw_name}\n"
            f'  IdentityFile "{self.tmp / "user"}"\n'
            "  IdentitiesOnly yes\n  BatchMode yes\n  StrictHostKeyChecking yes\n"
            f'  UserKnownHostsFile "{self.tmp / "known_hosts"}"\n'
            "  GlobalKnownHostsFile /dev/null\n"
            f"  ProxyCommand {shlex.join([sys.executable, str(proxy)])}\n"
            # Make native keepalives slower than the accelerated watchdog.
            "  ServerAliveInterval 60\n  ServerAliveCountMax 5\n"
            "  ControlMaster no\n  ControlPath none\n"
        )
        bin_path = self.tmp / "bin"
        bin_path.mkdir()
        client = bin_path / "ssh"
        client.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            f"with open({str(self.calls)!r}, 'a') as out:\n"
            "    out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            f"os.execv({SSH!r}, [{SSH!r}, '-F', {str(self.config)!r}, *sys.argv[1:]])\n"
        )
        client.chmod(0o700)
        self.env = {**os.environ, "PATH": f"{bin_path}:{os.environ['PATH']}"}
        self.patch = mock.patch.dict(os.environ, self.env)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.ssh = ssa.Ssh(HOST)
        self.ssh.config()

    def cleanup(self) -> None:
        for child in self.children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
            if child.stdin is not None:
                child.stdin.close()
        # A deliberately stopped server cannot handle the client's SIGTERM
        # until resumed. These PIDs belong only to this test's pipe servers.
        for pid in self.servers():
            try:
                os.kill(pid, signal.SIGCONT)
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for stream in self.streams:
            stream.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def servers(self) -> list[int]:
        return [int(pid) for pid in self.server_pids.read_text().splitlines()] \
            if self.server_pids.exists() else []

    def sessions(self) -> list[list[str]]:
        if not self.calls.exists():
            return []
        return [
            argv for line in self.calls.read_text().splitlines()
            if (argv := json.loads(line)) and "ControlMaster=yes" in argv
        ]

    def sink(self, name: str):
        stream = (self.tmp / name).open("w+b")
        self.streams.append(stream)
        return stream

    def until(self, condition, *, child=None, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = condition()
            if value:
                return value
            if child is not None and child.poll() is not None:
                break
            time.sleep(0.025)
        logs = "\n".join(p.read_text(errors="replace") for p in self.tmp.glob("*.log"))
        self.fail(f"SSH test did not reach expected state:\n{logs[-5000:]}")

    def start_master(self):
        path = str(self.tmp / "master")
        session = ssa.Session(ssa.parse([HOST]), watch=ssa.Watchdog(self.ssh))
        proc = subprocess.Popen(
            session.argv(path), stdin=subprocess.PIPE,
            stdout=self.sink("master.stdout"), stderr=self.sink("master.log"),
        )
        self.children.append(proc)
        self.until(lambda: Path(path).exists(), child=proc)
        # The socket is created before the initial session request completes.
        self.assertEqual(0, self.ssh._bounded(self.ssh.probe_argv(path), timeout=3)[0])
        return proc, path

    def test_frozen_transport_fails_even_when_a_fresh_connection_succeeds(self) -> None:
        master, path = self.start_master()
        os.kill(self.servers()[0], signal.SIGSTOP)
        # This is the old false signal: the local master answers while the
        # server on its transport is frozen, and a separate login works too.
        local_check = subprocess.run(
            ["ssh", "-S", path, "-O", "check", HOST],
            capture_output=True, timeout=3, check=False,
        )
        self.assertEqual(0, local_check.returncode)
        self.assertEqual(0, self.ssh.probe()[0])
        watch = ssa.Watchdog(self.ssh, control_path=path)
        self.addCleanup(watch.stop)
        with mock.patch.object(ssa, "WATCH_EVERY", 0.2), \
                mock.patch.object(ssa, "PROBE_WALL", 0.4):
            why = self.until(watch.tick, timeout=5)
        self.assertEqual(ssa.WEDGED, why.reason)
        self.assertIsNone(master.poll(), "native SSH exited before the watchdog detected the freeze")
        self.assertEqual(2, len(self.servers()), "a heartbeat opened another transport")

    def test_a_missing_socket_cannot_fall_back_to_a_successful_new_login(self) -> None:
        master, path = self.start_master()
        stopped = subprocess.run(
            ["ssh", "-S", path, "-O", "stop", HOST],
            capture_output=True, timeout=3, check=False,
        )
        self.assertEqual(0, stopped.returncode, stopped.stderr)
        self.until(lambda: not Path(path).exists())
        status, _ = self.ssh._bounded(self.ssh.probe_argv(path), timeout=3)
        self.assertNotEqual(0, status, "a new login falsely certified the original connection")
        self.assertEqual(1, len(self.servers()), "fallback invoked the real ProxyCommand")
        self.assertIsNone(master.poll(), "stop-listening should leave the existing session alive")

    def test_expired_proxy_credentials_leave_the_existing_connection_healthy(self) -> None:
        _, path = self.start_master()
        self.denied.touch()
        fresh, stderr = self.ssh.probe()
        self.assertNotEqual(0, fresh)
        self.assertIn("ExpiredToken", stderr)
        heartbeat, stderr = self.ssh._bounded(self.ssh.probe_argv(path), timeout=3)
        self.assertEqual(0, heartbeat, stderr)
        self.assertEqual(1, len(self.servers()))

    def test_supervisor_reconnects_after_the_original_transport_freezes(self) -> None:
        driver = self.tmp / "driver.py"
        driver.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(HERE)!r})\n"
            "from test_ssa import ssa\n"
            "ssa.WATCH_EVERY = 0.2\nssa.PROBE_WALL = 0.4\n"
            f"sys.exit(ssa.main([{HOST!r}]))\n"
        )
        proc = subprocess.Popen(
            [sys.executable, str(driver)], env=self.env, stdin=subprocess.PIPE,
            stdout=self.sink("supervisor.stdout"), stderr=self.sink("supervisor.log"),
        )
        self.children.append(proc)

        def ready(count):
            attempts = self.sessions()
            if len(attempts) < count:
                return None
            args = attempts[count - 1]
            path = args[args.index("-S") + 1]
            return path if Path(path).exists() else None

        first = self.until(lambda: ready(1), child=proc)
        # Ensure the shell opened before freezing its server.
        self.assertEqual(0, self.ssh._bounded(self.ssh.probe_argv(first), timeout=3)[0])
        os.kill(self.servers()[0], signal.SIGSTOP)
        second = self.until(lambda: ready(2), child=proc)
        self.assertNotEqual(first, second)
        self.assertEqual(0, self.ssh._bounded(self.ssh.probe_argv(second), timeout=3)[0])
        proc.stdin.write(b"exit\n")
        proc.stdin.flush()
        self.assertEqual(0, proc.wait(timeout=5))
        output = (self.tmp / "supervisor.log").read_text()
        self.assertIn("link dead: probe timed out", output)
        self.assertIn("back after", output)
        self.assertFalse(Path(first).parent.exists())
        self.assertFalse(Path(second).parent.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
