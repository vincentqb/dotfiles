#!/bin/bash

git submodule sync
git submodule update --init --recursive
~/dotfiles/dotpy/dot.py link default

chmod 700 ~/.ssh
chmod 600 ~/.ssh/*

/usr/bin/python3 -m pip install --upgrade pip
/usr/bin/python3 -m pip install --user -r requirements.txt

curl -L https://sw.kovidgoyal.net/kitty/installer.sh | sh /dev/stdin

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
export PATH=$PATH:/opt/homebrew/bin

brew update

brew install ripgrep bat fd
brew install nvim fish tmux
brew install shellcheck
brew install reattach-to-user-namespace
# brew install texlab
brew install --cask mactex-no-gui
# brew install fzf fasd
# brew install yarn
brew install wget
brew install ruff
brew install rsync
brew install eza
brew install zellij
brew install awscli
brew install just

brew install node
brew install --cask amazon-q

# https://wezterm.org/install/source.html#installing-from-source
# brew install --cask wezterm
# brew install --cask wezterm@nightly
# cargo install --branch=main --git https://github.com/wezterm/wezterm.git generate-bidi strip-ansi-escapes sync-color-schemes wezterm wezterm-gui
#
# ./ci/deploy.sh macos
# Drag and Drop WezTerm

# sshfs https://github.com/telepresenceio/telepresence/issues/1654#issuecomment-873538291
# brew install --cask macfuse
# brew install gromgit/fuse/sshfs-mac
# brew link --overwrite sshfs-mac

# brew install node
# npm install -g bash-language-server
# npm install -g diagnostic-languageserver
# npm install -g neovim yarn
# yarn global add neovim

sudo fish -c 'echo (which fish) >> /etc/shells'
chsh -s $(which fish)

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

# Use a modified version of the Pro theme by default in Terminal.app
# open "$HOME/dotfiles/terminal-app/Dracula.terminal"
# sleep 1  # Wait a bit to make sure the theme is loaded
# defaults write com.apple.terminal "Default Window Settings" -string "Dracula"
# defaults write com.apple.terminal "Startup Window Settings" -string "Dracula"

# Install anaconda
# brew install anaconda
# export PATH=$PATH:/opt/homebrew/anaconda3/bin
# conda init zsh fish

# Ensure all packages are up-to-date
brew upgrade
cargo install cargo-update
cargo install-update -a

# AMZN
kinit
mwinit -o
touch ~/toolbox-bootstrap.sh && \
  curl -X POST \
  --data '{"os":"osx"}' \
  -H "Authorization: $(curl -L \
  --cookie $HOME/.midway/cookie \
  --cookie-jar $HOME/.midway/cookie \
  "https://midway-auth.amazon.com/SSO?client_id=https://us-east-1.prod.release-service.toolbox.builder-tools.aws.dev&response_type=id_token&nonce=$RANDOM&redirect_uri=https://us-east-1.prod.release-service.toolbox.builder-tools.aws.dev:443")" \
  https://us-east-1.prod.release-service.toolbox.builder-tools.aws.dev/v1/bootstrap \
  > ~/toolbox-bootstrap.sh
bash ~/toolbox-bootstrap.sh
rm ~/toolbox-bootstrap.sh
source ~/.$(basename "$SHELL")rc
toolbox update
toolbox install ada axe
xcode-select --install

# install docker
# /opt/homebrew/opt/colima/bin/colima start -f
# brew install --cask docker
# brew install docker docker-compose colima
# docker replacement
# toolbox install finch

# Use hibernate (25) instead of sleep (3, default)
# https://discussions.apple.com/thread/255421002?sortBy=rank
pmset -g | grep hibernatemode
sudo pmset hibernatemode 25
pmset -g | grep hibernatemode
