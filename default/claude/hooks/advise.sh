#!/usr/bin/env bash
# PreToolUse: attach a reason to commands worth a second thought.
#
#   deny -> blocked; the reason reaches the model as an actionable error.
#
# Every branch here denies. `ask` is deliberately absent: it stalls the run on a
# prompt, and a subagent has no one to prompt, so it hangs until the turn dies.
# A matched `ask` rule also short-circuits auto mode's classifier outright
# (telemetry calls it `ask_rule`), so it forfeits the one thing that could have
# judged intent. A deny that explains itself and names the alternative is
# strictly better: the model revises instead of waiting.
#
# So every reason below must answer "then what?" — a denial with no next move is
# just a slower stall. Intent-dependent calls (git push, aws writes, force
# flags outside push) are NOT listed here on purpose; autoMode.soft_deny judges
# those against what the user actually asked for and denies with its own reason.
#
# Enforcement lives in permissions.deny — this hook fires unfiltered on every
# Bash call and exits immediately when nothing matches, so it's the prose, not
# the boundary. Matching is on the raw command string so `--force`, `-f`, `-rf`
# and `-fr` all land.
set -uo pipefail

cmd=$(jq -r '.tool_input.command // empty')
[ -n "$cmd" ] || exit 0

emit() { # $1 = allow|deny, $2 = reason (model sees it in both fields)
  jq -n --arg d "$1" --arg r "$2" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse",
                           permissionDecision: $d,
                           permissionDecisionReason: $r,
                           additionalContext: $r}}'
  exit 0
}

case $cmd in
  # --- The flag defeats the check rather than satisfying it. ---
  *--no-verify*|*--no-gpg-sign*)
    emit deny "Drop --no-verify and fix what the hook is failing on. The hook is
the check, not an obstacle to it — skipping it just moves the failure to CI or
to someone else's checkout. Run the hook, read what it says, fix that, commit
again. If the hook itself is wrong, fix the hook." ;;

  *core.hooksPath*)
    emit deny "Rerouting core.hooksPath turns hooks off globally, not just for
this command, and the next commit in every other repo silently skips its checks
too. Fix the failing hook instead." ;;

  # --- Privilege escalation. ---
  sudo*|*"| sudo "*|*"; sudo "*|*"&& sudo "*)
    emit deny "Nothing in this workspace needs root. If a command only works
under sudo, that's the signal it's touching system state it shouldn't — a global
package install where a project-local one belongs, or a path outside the
workspace. Do it unprivileged in the project, or hand the user the exact command
to run themselves." ;;

  # --- Destructive to the host. No agent-side alternative; the user runs it. ---
  shutdown*|reboot*|halt*|poweroff*|*mkfs*|*"of=/dev/"*)
    emit deny "This writes to a block device or takes the machine down, and
neither is recoverable from inside the session — a wrong target destroys a disk
or drops every other session on this host. There is no safer variant to
substitute. If it genuinely needs doing, tell the user what to run and why, and
let them run it." ;;

  # --- Force-push. Listed before the plain form so the safe one stays silent. ---
  *"push --force-with-lease"*)
    : ;;

  *"push --force"*|*"push -f "*|*"push -f")
    emit deny "Use --force-with-lease instead: it fails instead of overwriting a
ref someone else pushed. Plain --force cannot tell 'my rebase' from 'their
commits' and discards both. If the remote merely moved, --force-with-lease is
the whole fix; if overwriting published history is the actual intent, that's the
user's call to make, so ask them rather than doing it." ;;

  # --- rm -r is enough; the -f only hides the error that would save you. ---
  *"rm -rf"*|*"rm -fr"*|*"rm -r -f"*|*"rm -f -r"*)
    emit deny "Re-run with -r and no -f. The -f only suppresses the errors that
would tell you the path was wrong — a typo'd path fails loudly under -r and
silently deletes nothing under -rf, so you learn about it later. rm -r deletes a
scratch dir fine, read-only .git/objects included. If the path may legitimately
not exist, guard it: [ -d \"\$D\" ] && rm -r \"\$D\"." ;;
esac

exit 0
