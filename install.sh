#!/bin/bash

# Install dotfiles using bashdot

git submodule sync
git submodule update --init --recursive
~/dotfiles/bashdot/bashdot install default

# Install dependencies

/usr/bin/pip3 install --user -r requirements.txt

if [ "$1" = "mac" ]; then
    # MacOS

    # Neovim
    wget https://github.com/neovim/neovim/releases/download/stable/nvim-macos.tar.gz
    tar xzvf nvim-macos.tar.gz
    mv ./nvim-osx64/bin/nvim "$BIN_DIR/nvim"

    # Fix copy-paste in MacOS
    brew install reattach-to-user-namespace

    # Spell checker for pylint
    brew install enchant
    # export PYENCHANT_LIBRARY_PATH=/Users/vincentqb/homebrew/lib/libenchant-2.dylib
    # pylint --disable all --enable spelling --spelling-dict en_US file.py

    brew install shellcheck

    # Only use UTF-8 in Terminal.app
    # defaults write com.apple.terminal StringEncodings -array 4

    # Use a modified version of the Pro theme by default in Terminal.app
    open "$HOME/dotfiles/terminal-app/Dracula.terminal"
    sleep 1  # Wait a bit to make sure the theme is loaded
    defaults write com.apple.terminal "Default Window Settings" -string "Dracula"
    defaults write com.apple.terminal "Startup Window Settings" -string "Dracula"

    brew install fzf fasd

    brew install texlab
    brew install --cask mactex-no-gui

else
    # Linux

    # Neovim
    wget https://github.com/neovim/neovim/releases/download/stable/nvim.appimage -O "$BIN_DIR/nvim"
    chmod u+x "$BIN_DIR/nvim"

    # bashls
    # sudo snap install bash-language-server

    # scala
    curl -fLo cs https://git.io/coursier-cli-"$(uname | tr LD ld)"
    chmod +x cs
    ./cs install metals
    export PATH="$PATH:/home/ubuntu/.local/share/coursier/bin"\

fi

# Install node.js
nvm install node
npm install -g neovim

# Install language servers
npm install -g pyright
npm install -g bash-language-server

# diagnostic-language server
npm install -g yarn
# export PATH="$(yarn global bin):$PATH"
yarn global add diagnostic-languageserver

# Instal miniconda

wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p ~/miniconda
eval "$(~/miniconda/bin/conda shell.bash hook)"
source ~/miniconda/bin/activate
conda init zsh

# Update tpm

~/.tmux/plugins/tpm/bin/update_plugins all	# prefix + U
~/.tmux/plugins/tpm/bin/clean_plugins	    # prefix + alt + u
~/.tmux/plugins/tpm/bin/install_plugins	    # prefix + I

# Update zsh

zgen selfupdate
zgen reset
zgen update