#!/usr/bin/fish

# Extend $PATH
fish_add_path $HOME/bin $HOME/.local/bin $HOME/homebrew/bin $HOME/homebrew/sbin

# Install plugin manager
curl -sL https://git.io/fisher | source && fisher install jorgebucaran/fisher

# Configure nvm
fisher install jorgebucaran/nvm.fish
nvm install latest

# Configure prompt
# fish_config prompt choose terlar
# fisher install dracula/fish
fisher install pure-fish/pure

# Set vim keybindings
fish_vi_key_bindings

# Point vim to nvim
alias vim="nvim"
funcsave vim

# Set n/vim as default editor
set -U EDITOR vim
set -U VISUAL vim
set -U TEXEDIT "vim %s"
set -U GIT_EDITOR vim
