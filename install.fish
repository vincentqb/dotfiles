#!/opt/homebrew/bin/fish

# Extend $PATH
fish_add_path $HOME/bin $HOME/.local/bin $HOME/homebrew/bin $HOME/homebrew/sbin /opt/homebrew/bin

# Install plugin manager
curl -sL https://git.io/fisher | source && fisher install jorgebucaran/fisher

# Configure nvm
fisher install jorgebucaran/nvm.fish
nvm install latest
npm install -g neovim yarn
yarn global add neovim

# Configure prompt
# fish_config prompt choose terlar
# fisher install dracula/fish
fisher install pure-fish/pure

# Set vim keybindings
fish_vi_key_bindings

# Set n/vim as default editor
set -U EDITOR nvim
set -U VISUAL nvim
set -U TEXEDIT "nvim %s"
set -U GIT_EDITOR nvim

# Point vim to nvim in userspace
alias vim="nvim"
funcsave vim

# Install anaconda for fish
conda init fish
conda config --set changeps1 False