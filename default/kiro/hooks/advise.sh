#!/usr/bin/env bash
# Kiro preToolUse: attach a reason to commands worth a second thought.
#
# The port of ../../claude/hooks/advise.sh. Same reasons, different contract:
#
#   exit 0 -> allow.
#   exit 2 -> block; stderr reaches the user AND the model, so it lands as an
#             actionable error rather than a bare refusal.
#
# Kiro has no `ask` tier to remove, but it has the same failure shape by
# omission: anything that matches no rule falls through to a prompt, and a
# prompt is a stall for a delegated agent with no one to answer it. Worse, an
# "ask"-level prompt has been measured getting auto-accepted by the client in
# autopilot mode (13 unintended Slack deletions passed the permission layer and
# were stopped only by a preToolUse hook). So the prompt tier is unreliable in
# both directions, and the fix is the same as on the Claude side: decide here,
# with a reason, and never leave it to a prompt.
#
# Enforcement belongs in toolsSettings.shell.deniedCommands, which blocks
# without prompting. This hook is the prose, plus the one thing a full-string
# regex cannot do: it splits on && || ; | so an anchored pattern like `sudo*`
# still fires on `ls && sudo rm x`. It filters by tool name itself rather than
# relying on a matcher, so the shell/execute_bash alias split can't silently
# disable it.
set -uo pipefail

payload=$(cat)
tool=$(printf '%s' "$payload" | jq -r '.tool_name // empty')
cmd=$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')

# Only shell invocations carry a command; everything else is none of our business.
case $tool in
  shell|execute_bash|executeBash|execute_cmd|executeCmd|"") ;;
  *) exit 0 ;;
esac
[ -n "$cmd" ] || exit 0

deny() { printf '%s\n' "$1" >&2; exit 2; }

check() { # $1 = one command segment
  case $1 in
    *--no-verify*|*--no-gpg-sign*)
      deny "Drop --no-verify and fix what the hook is failing on. The hook is
the check, not an obstacle to it — skipping it just moves the failure to CI or
to someone else's checkout. Run the hook, read what it says, fix that, commit
again. If the hook itself is wrong, fix the hook." ;;

    *core.hooksPath*)
      deny "Rerouting core.hooksPath turns hooks off globally, not just for this
command, and the next commit in every other repo silently skips its checks too.
Fix the failing hook instead." ;;

    sudo\ *|sudo)
      deny "Nothing in this workspace needs root. If a command only works under
sudo, that's the signal it's touching system state it shouldn't — a global
package install where a project-local one belongs, or a path outside the
workspace. Do it unprivileged in the project, or hand the user the exact command
to run themselves." ;;

    shutdown*|reboot*|halt*|poweroff*|*mkfs*|*of=/dev/*)
      deny "This writes to a block device or takes the machine down, and neither
is recoverable from inside the session — a wrong target destroys a disk or drops
every other session on this host. There is no safer variant to substitute. If it
genuinely needs doing, tell the user what to run and why, and let them run it." ;;

    *push*--force-with-lease*)
      : ;;

    *push*--force*|*push\ -f\ *|*push\ -f)
      deny "Use --force-with-lease instead: it fails instead of overwriting a ref
someone else pushed. Plain --force cannot tell 'my rebase' from 'their commits'
and discards both. If the remote merely moved, --force-with-lease is the whole
fix; if overwriting published history is the actual intent, that's the user's
call to make, so ask them rather than doing it." ;;

    *rm\ -rf*|*rm\ -fr*|*rm\ -r\ -f*|*rm\ -f\ -r*)
      deny "Re-run with -r and no -f. The -f only suppresses the errors that
would tell you the path was wrong — a typo'd path fails loudly under -r and
silently deletes nothing under -rf, so you learn about it later. rm -r deletes a
scratch dir fine, read-only .git/objects included. If the path may legitimately
not exist, guard it: [ -d \"\$D\" ] && rm -r \"\$D\"." ;;
  esac
}

# Test the whole string first, then each segment, so both a chained command and
# an anchored pattern inside one get caught.
check "$cmd"
segs=$cmd
segs=${segs//&&/$'\n'}
segs=${segs//||/$'\n'}
segs=${segs//;/$'\n'}
segs=${segs//|/$'\n'}
while IFS= read -r seg; do
  seg=${seg#"${seg%%[![:space:]]*}"}   # ltrim
  [ -n "$seg" ] && check "$seg"
done <<< "$segs"

exit 0
