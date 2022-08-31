#!/bin/bash

git submodule sync
git submodule update --init --recursive
~/dotfiles/bashdot/bashdot install default

/usr/bin/pip3 install --user -r requirements.txt

# Install latest neovim
wget https://github.com/neovim/neovim/releases/download/stable/nvim-macos.tar.gz
tar xzvf nvim-macos.tar.gz
mv ./nvim-osx64/bin/nvim ~/.local/bin/nvim

# Update vim plugins
~/.local/bin/nvim +PackClean +qa
~/.local/bin/nvim +PackUpdate +qa

brew install fish
brew install tmux
brew install shellcheck
brew install reattach-to-user-namespace
brew install texlab
brew install --cask mactex-no-gui
# brew install fzf fasd

# Spell checker for pylint
# brew install enchant
# export PYENCHANT_LIBRARY_PATH=/Users/vincentqb/homebrew/lib/libenchant-2.dylib
# pylint --disable all --enable spelling --spelling-dict en_US file.py

~/.tmux/plugins/tpm/bin/update_plugins all	# prefix + U
~/.tmux/plugins/tpm/bin/clean_plugins	    # prefix + alt + u
~/.tmux/plugins/tpm/bin/install_plugins	    # prefix + I

# Only use UTF-8 in Terminal.app
# defaults write com.apple.terminal StringEncodings -array 4

# Use a modified version of the Pro theme by default in Terminal.app
open "$HOME/dotfiles/terminal-app/Dracula.terminal"
sleep 1  # Wait a bit to make sure the theme is loaded
defaults write com.apple.terminal "Default Window Settings" -string "Dracula"
defaults write com.apple.terminal "Startup Window Settings" -string "Dracula"

# Install anaconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p ~/miniconda
eval "$(~/miniconda/bin/conda shell.bash hook)"
source ~/miniconda/bin/activate
conda init zsh
conda init fish
