# Command hygiene

Kiro enforces this with `toolsSettings.shell.deniedCommands` regex lists in the
agent config. Those blocks give no reason, so the reasoning lives here.

## Never skip a check to get past it

- **`--no-verify` / `--no-gpg-sign`**: remove the flag and fix what the hook is
  failing on. The hook is the check, not an obstacle to it — skipping it moves
  the failure to CI or to someone else's checkout. Run the hook, read what it
  says, fix that, commit again. If the hook itself is wrong, fix the hook.
- **`core.hooksPath`**: rerouting it turns hooks off globally, not just for the
  command at hand, so the next commit in every other repo silently skips its
  checks too.

## Prefer the flag that fails loudly

- **`--force`**: try again without it first. If the push was rejected because
  the remote moved, use `--force-with-lease` — it fails instead of overwriting a
  ref someone else pushed. Plain `--force` cannot tell "my rebase" from "their
  commits" and discards both. Reach for it only when the overwrite is the intent.
- **`rm -rf`**: `rm -r` is enough. The `-f` only suppresses the errors that would
  tell you the path was wrong — a typo'd path fails loudly under `-r` and
  silently under `-rf`. Use `-r` unless the force is deliberate (read-only files,
  or a path that may legitimately not exist).

Claude Code carries the same rules in `default/claude/hooks/advise.sh`, which
attaches these explanations to the permission decision at call time.
