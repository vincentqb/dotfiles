# Homebrew otherwise starts mise in every Fish process and adds a subprocess to
# each prompt. This setup uses uv, rustup and Homebrew; use `mise exec` as needed.
# Opt in to automatic project environments with:
#     env MISE_FISH_AUTO_ACTIVATE=1 fish
# Prompt workers inherit the parent's environment and need no activation.
if not status is-interactive; or not set -q MISE_FISH_AUTO_ACTIVATE
    set -gx MISE_FISH_AUTO_ACTIVATE 0
end
