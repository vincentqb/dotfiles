#!/usr/bin/env bash
# PreToolUse: attach a reason to commands worth a second thought.
#
#   deny -> blocked; the reason reaches the model as an actionable error.
#   ask  -> the prompt still fires, and additionalContext hands the model the
#           reason so it can revise instead of just re-asking. A bare `ask`
#           tells the model nothing but "not granted yet", hence both fields.
#
# Enforcement lives in permissions.deny — the `if:` filter fails open on Bash
# it can't parse, so this file is for the prose, not the boundary. Matching is
# on the raw command string so `--force`, `-f`, `-rf` and `-fr` all land.
set -uo pipefail

cmd=$(jq -r '.tool_input.command // empty')
[ -n "$cmd" ] || exit 0

emit() { # $1 = allow|deny|ask, $2 = reason (model sees it in both fields)
  jq -n --arg d "$1" --arg r "$2" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse",
                           permissionDecision: $d,
                           permissionDecisionReason: $r,
                           additionalContext: $r}}'
  exit 0
}

case $cmd in
  # --- Hard blocks: the flag defeats the check rather than satisfying it. ---
  *--no-verify*|*--no-gpg-sign*)
    emit deny "Drop --no-verify and fix what the hook is failing on. The hook is
the check, not an obstacle to it — skipping it just moves the failure to CI or
to someone else's checkout. Run the hook, read what it says, fix that, commit
again. If the hook itself is wrong, fix the hook." ;;

  *core.hooksPath*)
    emit deny "Rerouting core.hooksPath turns hooks off globally, not just for
this command, and the next commit in every other repo silently skips its checks
too. Fix the failing hook instead." ;;

  # --- Soft: prompt, but tell the model what to try first. ---
  # Listed before --force* so the safe form wins the match and stays silent.
  *--force-with-lease*)
    : ;;
  *--force*|*"push -f"*)
    emit ask "Try again without --force first. If it was rejected because the
remote moved, use --force-with-lease: it fails instead of overwriting a ref
someone else pushed. Plain --force cannot tell 'my rebase' from 'their commits'
and discards both. Only reach for it when the overwrite is the actual intent." ;;

  *"rm -rf"*|*"rm -fr"*|*"rm -r -f"*|*"rm -f -r"*)
    emit ask "rm -r is enough. The -f only suppresses the errors that would tell
you the path was wrong — a typo'd path fails loudly under -r and silently under
-rf. Re-run with -r unless the force is deliberate (read-only files, a path that
may legitimately not exist)." ;;
esac

exit 0
