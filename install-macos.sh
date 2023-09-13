#!/bin/bash

git submodule sync
git submodule update --init --recursive
~/dotfiles/bashdot/bashdot install default

/usr/bin/pip3 install --user --upgrade -r requirements.txt

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
export PATH=$PATH:/opt/homebrew/bin

brew install ripgrep bat fd
brew install nvim fish tmux
brew install shellcheck
brew install reattach-to-user-namespace
brew install texlab
brew install --cask mactex-no-gui
# brew install fzf fasd
brew install yarn
brew install wget

brew install node
npm install -g bash-language-server
npm install -g diagnostic-languageserver
npm install -g neovim yarn
yarn global add neovim

# Update nvim plugins
nvim --headless +PackClean +qa
nvim --headless +PackUpdate +qa
nvim --headless +DirtytalkUpdate +qa

# Spell checker for pylint
# brew install enchant
# export PYENCHANT_LIBRARY_PATH=/Users/vincentqb/homebrew/lib/libenchant-2.dylib
# pylint --disable all --enable spelling --spelling-dict en_US file.py

~/.tmux/plugins/tpm/bin/update_plugins all	# prefix + U
~/.tmux/plugins/tpm/bin/clean_plugins	    # prefix + alt + u
~/.tmux/plugins/tpm/bin/install_plugins	    # prefix + I

# Only use UTF-8 in Terminal.app
# defaults write com.apple.terminal StringEncodings -array 4

# Install zellij to use instead of tmux
mkdir -p ~/.local/bin
wget -qO- https://github.com/zellij-org/zellij/releases/download/v0.34.4/zellij-aarch64-apple-darwin.tar.gz | tar xvpz -C ~/.local/bin

# Use a modified version of the Pro theme by default in Terminal.app
# open "$HOME/dotfiles/terminal-app/Dracula.terminal"
# sleep 1  # Wait a bit to make sure the theme is loaded
# defaults write com.apple.terminal "Default Window Settings" -string "Dracula"
# defaults write com.apple.terminal "Startup Window Settings" -string "Dracula"

# Install anaconda
brew install anaconda
export PATH=$PATH:/opt/homebrew/anaconda3/bin
conda init zsh fish

brew update
brew upgrade

# AMZN
xcode-select --install
toolbox install ada axe
