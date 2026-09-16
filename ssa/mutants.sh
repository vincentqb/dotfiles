#!/usr/bin/env bash
# Every check must be able to fail. Break one thing, run the check that claims to
# catch it, and require it to go red -- a check that survives its mutant is
# decoration.
set -u
cd "$(dirname "$0")" || exit 1

mutate() {
    cp ssa /tmp/ssa.bak
    python3 - "$1" "$2" <<'PY'
import pathlib, sys
p = pathlib.Path("ssa")
text = p.read_text()
old, new = sys.argv[1], sys.argv[2]
if text.count(old) != 1:
    sys.exit(f"mutant anchor matched {text.count(old)} times: {old!r}")
p.write_text(text.replace(old, new))
PY
}

killed=0
survived=0
check() { # check LABEL TEST...
    local label=$1
    shift
    if timeout 200 python3 test_ssa.py "$@" >/tmp/mutant.log 2>&1; then
        survived=$((survived + 1))
        printf 'SURVIVED  %s\n' "$label"
    else
        killed=$((killed + 1))
        printf 'killed    %s\n' "$label"
    fi
    mv /tmp/ssa.bak ssa
}

mutate 'if self.options.command:' 'if False:'
check 'a remote command is replayed after an ambiguous 255' \
    Behaviour.test_a_dropped_remote_command_runs_once_and_says_why

mutate 'Rule(Class.FATAL, "host key changed", "IDENTIFICATION HAS CHANGED"),' \
    'Rule(Class.CONNECT, "host key changed", "IDENTIFICATION HAS CHANGED"),'
check 'a changed host key becomes retryable' \
    Behaviour.test_a_changed_host_key_stops_naming_the_ambiguity

mutate 'argv = ["ssh", "-o", "BatchMode=yes"]' 'argv = ["ssh"]'
check 'the session may prompt' Interface.test_the_session_cannot_prompt

mutate 'return "\n".join(keep[-lines:])' 'return "\n".join(keep)'
check 'the whole of stderr is searched' \
    Classifier.test_a_line_from_an_attempt_that_recovered_is_not_the_reason

mutate 'if why.key != self.last or self.clock() - self.noted >= NOTE_EVERY:' \
    'if why.reason != self.last or self.clock() - self.noted >= NOTE_EVERY:'
check 'the rendered reason is compared, so a duration defeats the cadence' \
    Cadence.test_a_ticking_duration_does_not_defeat_the_cadence

mutate 'status = proc.wait(timeout=PROBE_WALL)' 'status = proc.wait()'
check 'a probe has no bound' Behaviour.test_a_probe_that_will_not_return_is_cut_off

mutate 'if select.select([fd], [], [], left)[0] and os.read(fd, 1) == b"q":' \
    'if select.select([fd], [], [], left)[0] and os.read(fd, 1):'
check 'any key stops the reconnect' \
    Terminal.test_a_queued_escape_sequence_does_not_abort_the_reconnect

mutate '"ControlMaster=no",' '"ControlPath=none",'
check 'the probe insists on a fresh handshake' \
    Interface.test_the_probe_adds_only_options_that_bound_the_attempt

mutate 'if token == "--tmux":' 'if token == "--never-matches":'
check '--tmux eats the next token' \
    Interface.test_a_host_that_looks_like_a_session_name_is_still_the_host

mutate 'for sig in (signal.SIGCONT, signal.SIGTERM):' 'for sig in (signal.SIGTERM,):'
check 'a stopped child is never resumed, so TERM cannot reach it' \
    Behaviour.test_a_stopped_session_is_resumed_so_term_can_reach_it

mutate 'if status != EXIT_AMBIGUOUS:' 'if status not in (0, EXIT_AMBIGUOUS):'
check 'a clean logout is treated as ambiguous' \
    Behaviour.test_a_clean_exit_is_zero_and_does_not_reconnect

mutate 'self.ssh.drop_stale_master()' 'pass  # dropped'
check 'a stale control socket is never dropped' \
    Behaviour.test_the_stale_master_check_precedes_the_first_probe

printf '\n%d killed, %d survived\n' "$killed" "$survived"
[[ $survived -eq 0 ]]
