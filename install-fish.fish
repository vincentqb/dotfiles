#!/usr/bin/env fish

# Extend $PATH
fish_add_path $HOME/bin $HOME/.local/bin
fish_add_path $HOME/homebrew/bin $HOME/homebrew/sbin /opt/homebrew/bin
fish_add_path $HOME/.toolbox/bin
fish_add_path $HOME/.cargo/bin
fish_add_path /home/linuxbrew/.linuxbrew/bin/

# Install fisher + plugins declared in default/config/fish/fish_plugins
curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source; and fisher install jorgebucaran/fisher
fisher update

# Kiro's Fish integration currently only adds ~/.local/bin, already on PATH.
# These legacy Fig hooks launch the CLI twice in every shell and prompt worker.
# Fish provides completions and autosuggestions itself.
rm -f "$__fish_config_dir/conf.d/00_fig_pre.fish" "$__fish_config_dir/conf.d/99_fig_post.fish"

# Return to default keybindings
fish_default_key_bindings
rm -f ~/.config/fish/functions/fish_user_key_bindings.fish

# Default editor
set -Ux EDITOR vim
set -Ux VISUAL vim
set -Ux TEXEDIT "vim %s"
set -Ux GIT_EDITOR vim

# eza color scheme (Dracula-inspired)
# https://github.com/dracula/exa/blob/main/exa_colors.zshrc
set -Ux EZA_COLORS "\
uu=36:\
gu=37:\
sn=32:\
sb=32:\
da=34:\
ur=34:\
uw=35:\
ux=36:\
ue=36:\
gr=34:\
gw=35:\
gx=36:\
tr=34:\
tw=35:\
tx=36:"

# Disable welcome message
set -U fish_greeting ""

# Use Claude Code through Bedrock
set -Ux CLAUDE_CODE_USE_BEDROCK 1
