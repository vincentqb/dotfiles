#!/usr/bin/fish

# Extend $PATH
fish_add_path $HOME/bin $HOME/.local/bin $HOME/homebrew/bin $HOME/homebrew/sbin /opt/homebrew/bin

# Install plugin manager
curl -sL https://git.io/fisher | source && fisher install jorgebucaran/fisher

# Configure prompt
# fish_config prompt choose terlar
# fisher install dracula/fish
fisher install acomagu/fish-async-prompt
fisher install pure-fish/pure
set -U async_prompt_functions _pure_prompt_git

# Set vim keybindings
fish_vi_key_bindings

# Enable CTRL+F to accept autocomplete
# https://github.com/fish-shell/fish-shell/issues/3541
function fish_user_key_bindings
    for mode in insert default visual
        bind -M $mode \cf forward-char
    end
end
funcsave fish_user_key_bindings

# Set n/vim as default editor
set -Ux EDITOR nvim
set -Ux VISUAL nvim
set -Ux TEXEDIT "nvim %s"
set -Ux GIT_EDITOR nvim

# Point vim to nvim in userspace
alias vim="nvim"
funcsave vim
alias vimdiff="nvim -d"
funcsave vimdiff

# Configure node.js to use with language servers
fisher install jorgebucaran/nvm.fish
nvm install latest
npm install -g neovim yarn
npm install -g bash-language-server diagnostic-languageserver
yarn global add neovim

# Install anaconda for fish
conda init fish
conda config --set changeps1 False
