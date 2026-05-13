#!/bin/bash

git submodule sync
git submodule update --init --recursive

chmod 700 ~/.ssh
chmod 600 ~/.ssh/*

# Homebrew + everything in the Brewfile (formulae, casks, cargo, uv tools)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/opt/homebrew/bin/brew shellenv)"
brew update
brew bundle

# Neovim plugins via lazy.nvim
nvim --headless "+Lazy! sync" +qa

# Fish as default shell
sudo fish -c 'echo (which fish) >> /etc/shells'
chsh -s $(which fish)

# Keep cargo crates fresh
cargo install-update -a

# AMZN toolbox
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
toolbox install ada axe brazilcli cr claude-code aim
brazil setup completion
aim plugins install AmazonBuilderCoreAIAgents
xcode-select --install

# Hibernate (25) instead of sleep (3) on lid close
# https://discussions.apple.com/thread/255421002
sudo pmset hibernatemode 25

# VS Code: disable press-and-hold so vim keybindings repeat
defaults write com.microsoft.VSCode ApplePressAndHoldEnabled -bool false
