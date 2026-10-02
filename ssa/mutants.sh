#!/usr/bin/env bash
# Break selected behaviors in disposable copies. Validate anchors and baseline
# tests first, so a broken harness cannot masquerade as a detected regression.
set -euo pipefail
exec python3 - "$(dirname "$0")" <<'PY'
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
source = (root / "ssa").read_text()
# label, exact replacement, replacement text, test name
cases = [
    ("remote command replay",
     "if self.options.command:", "if False:",
     "Behaviour.test_a_dropped_remote_command_runs_once_and_says_why"),
    ("host-key change becomes retryable",
     'Rule(Class.FATAL, "host key changed", "IDENTIFICATION HAS CHANGED"),',
     'Rule(Class.CONNECT, "host key changed", "IDENTIFICATION HAS CHANGED"),',
     "Behaviour.test_a_changed_host_key_stops_naming_the_ambiguity"),
    ("session may prompt",
     '"ssh", "-o", "BatchMode=yes", "-o", "ControlMaster=yes",',
     '"ssh", "-o", "ControlMaster=yes",',
     "Interface.test_the_session_cannot_prompt"),
    ("old stderr dictates the failure",
     r'return "\n".join(keep[-lines:])', r'return "\n".join(keep)',
     "Classifier.test_a_line_from_an_attempt_that_recovered_is_not_the_reason"),
    ("ticking duration defeats print cadence",
     "if why.key != self.last or self.clock() - self.noted >= NOTE_EVERY:",
     "if why.reason != self.last or self.clock() - self.noted >= NOTE_EVERY:",
     "Cadence.test_a_ticking_duration_does_not_defeat_the_cadence"),
    ("unbounded readiness probe",
     "status = proc.wait(timeout=timeout)", "status = proc.wait()",
     "Behaviour.test_a_probe_that_will_not_return_is_cut_off"),
    ("any queued key aborts recovery",
     'if select.select([fd], [], [], left)[0] and os.read(fd, 1) == b"q":',
     "if select.select([fd], [], [], left)[0] and os.read(fd, 1):",
     "Terminal.test_a_queued_escape_sequence_does_not_abort_the_reconnect"),
    ("readiness can reuse a shared master",
     'transport = ["-o", "ControlPath=none"]',
     'transport = []',
     "Interface.test_a_readiness_probe_requires_a_fresh_connection"),
    ("tmux argument parsing",
     'if token == "--tmux":', 'if token == "--never-matches":',
     "Interface.test_a_host_that_looks_like_a_session_name_is_still_the_host"),
    ("stopped child cannot handle TERM",
     "for sig in (signal.SIGCONT, signal.SIGTERM):",
     "for sig in (signal.SIGTERM,):",
     "Behaviour.test_a_stopped_session_is_resumed_so_term_can_reach_it"),
    ("clean logout reconnects",
     "if status != EXIT_AMBIGUOUS:", "if status not in (0, EXIT_AMBIGUOUS):",
     "Behaviour.test_a_clean_exit_is_zero_and_does_not_reconnect"),
    ("session does not own its transport",
     '"ssh", "-o", "BatchMode=yes", "-o", "ControlMaster=yes",',
     '"ssh", "-o", "BatchMode=yes", "-o", "ControlMaster=no",',
     "Interface.test_the_session_owns_a_foreground_master"),
    ("dead link is never declared",
     "if self.fails >= WATCH_FAILS:", "if False:",
     "Watch.test_a_dead_link_is_noticed_and_the_session_dropped"),
    ("connection resets are ignored",
     "self.fails += 1", "self.fails += int(why.cls is Class.CONNECT)",
     "Watch.test_connection_reset_counts_as_a_failed_heartbeat"),
    ("resume waits for normal cadence",
     "if slept > RESUME_JUMP:", "if False:",
     "Watch.test_a_resume_probes_at_once_instead_of_on_the_cadence"),
    ("watchdog kill looks like remote exit",
     "killed = self.session.why", "killed = None",
     "Watch.test_a_watchdog_kill_reconnects_without_a_grace_window"),
    ("heartbeat can certify a different transport",
     'transport = ["-S", control_path, "-o", "ProxyCommand=false"]',
     'transport = ["-S", control_path]',
     "Interface.test_a_heartbeat_cannot_fall_back_to_a_fresh_connection"),
    ("stderr EOF disables supervision",
     "reading = False", "break",
     "Watch.test_closed_stderr_does_not_disable_the_watchdog"),
    ("connection setup waits forever",
     "elif now - self.started >= self.ssh.connect_wall:", "elif False:",
     "Watch.test_a_hung_connection_setup_is_stopped"),
    ("forced shutdown leaves raw terminal mode",
     "termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, saved)", "pass",
     "Terminal.test_the_terminal_is_restored_when_ssh_requires_sigkill"),
    ("pre-suspend heartbeat stays blocked",
     "self.deadline = now  # an in-flight heartbeat is stale too",
     "pass  # leave the old heartbeat deadline",
     "Watch.test_resume_expires_an_inflight_heartbeat"),
    ("noisy stderr hides process exit",
     "if status is None:\n                    status = proc.poll()",
     "if False:\n                    status = proc.poll()",
     "Behaviour.test_a_noisy_descendant_cannot_hide_the_session_exit"),
]
if os.environ.get("SSA_TEST_SSHD"):
    # Exercise the mux fallback fault with real SSH as well as argv checks.
    cases.append((
        "real SSH fallback accepts a fresh login",
        'transport = ["-S", control_path, "-o", "ProxyCommand=false"]',
        'transport = ["-S", control_path]',
        "test_ssh.OpenSSH.test_a_missing_socket_cannot_fall_back_to_a_successful_new_login",
    ))

for label, old, new, test in cases:
    if source.count(old) != 1:
        sys.exit(f"Invalid mutation {label!r}: anchor matched {source.count(old)} times")
    compile(source.replace(old, new), "ssa", "exec")

def test_name(name):
    return name if name.startswith("test_") else "test_ssa." + name

with tempfile.TemporaryDirectory(prefix="ssa-mutants-") as directory:
    work = Path(directory)
    for name in ("ssa", "test_ssa.py", "test_ssh.py"):
        shutil.copy2(root / name, work / name)
    # Equal-sized edits within the same second must not reuse bytecode.
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    def run(names):
        try:
            return subprocess.run(
                [sys.executable, "-m", "unittest", "-v", *names],
                cwd=work, env=env, capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired:
            sys.exit("Mutation test runner timed out; this is not a detected regression")

    print("Checking selected tests on the original source...", flush=True)
    baseline = run(list(dict.fromkeys(test_name(case[3]) for case in cases)))
    if baseline.returncode != 0 or "skipped=" in baseline.stderr:
        print(baseline.stdout + baseline.stderr)
        sys.exit("Baseline did not pass every selected test; mutations were not run")

    detected = survived = 0
    for label, old, new, test in cases:
        (work / "ssa").write_text(source.replace(old, new))
        result = run([test_name(test)])
        if result.returncode == 1 and ("FAIL:" in result.stderr or "ERROR:" in result.stderr):
            detected += 1
            print(f"detected  {label}", flush=True)
        elif result.returncode == 0:
            survived += 1
            print(f"SURVIVED  {label}", flush=True)
        else:
            print(result.stdout + result.stderr)
            sys.exit(f"Unexpected test runner failure for {label!r}")
    print(f"\n{detected} detected, {survived} survived", flush=True)
    sys.exit(bool(survived))
PY
