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
  (cd "$w/src" && slot ./lake build vera)
  mkdir -p ~/.local/share/vera
  cp "$w/src/.lake/build/bin/vera" "$dest.new" && mv "$dest.new" "$dest"
  cp "$w/src/.lake/build/bin/vera.commit" ~/.local/share/vera/vera.commit
  git -C "$repo" worktree remove "$w/src" && rm -r "$w"
fi
"$dest" check < /dev/null
ln -sfn "$dest" ~/.local/bin/vera.new && mv -T ~/.local/bin/vera.new ~/.local/bin/vera
echo "$c" > vera.commit
