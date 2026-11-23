#!/bin/bash
# usage: install-vera.sh [commit]   installs VERA at the commit in vera.commit, or at the given one, which then
# replaces it once `vera check` passes on ~/.config/vera with the new binary
set -e
cd "$(dirname "$0")"
repo=${VERA_REPO:-/local/home/quennv/VERA}
c=$(git -C "$repo" rev-parse "${1:-$(cat vera.commit)}")
dest=~/.local/share/vera/vera-${c:0:7}
slot() { if [ -x /tmp/vera-lanes/slot.sh ]; then /tmp/vera-lanes/slot.sh "$@"; else "$@"; fi; }
if [ ! -x "$dest" ]; then
  w=$(mktemp -d /dev/shm/vera-install.XXXXXX)
  git -C "$repo" worktree add --detach "$w/src" "$c" > /dev/null
  (cd "$w/src" && slot ./lake build vera veraCommit)
  mkdir -p ~/.local/share/vera
  # the commit file first: an install cut short leaves no binary, so the next run redoes both
  cp "$w/src/.lake/build/bin/vera.commit" "$dest.commit.new" && mv "$dest.commit.new" "$dest.commit"
  cp "$w/src/.lake/build/bin/vera" "$dest.new" && mv "$dest.new" "$dest"
  git -C "$repo" worktree remove "$w/src" && rm -r "$w"
fi
# from 5d23160 on, a build says the commit it was built from: it must be the one asked for
if git -C "$repo" merge-base --is-ancestor 5d23160 "$c"; then
  v=$("$dest" --version) && [ "$v" = "$c" ] || { echo "install-vera.sh: $dest --version said '$v', not $c" >&2; exit 1; }
fi
"$dest" check < /dev/null
ln -sfn "$dest" ~/.local/bin/vera.new && mv -T ~/.local/bin/vera.new ~/.local/bin/vera
echo "$c" > vera.commit
