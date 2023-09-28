#!/bin/bash

git submodule sync
git submodule update --init --recursive
~/dotfiles/bashdot/bashdot install default

/usr/bin/pip3 install --user -r requirements.txt

# Install latest neovim
mkdir -p ~/.local/bin
wget https://github.com/neovim/neovim/releases/download/stable/nvim.appimage -O ~/.local/bin/nvim
chmod +x ~/.local/bin/nvim

# Update nvim plugins
~/.local/bin/nvim --headless +PackClean +qa
~/.local/bin/nvim --headless +PackUpdate +qa
~/.local/bin/nvim --headless +DirtytalkUpdate +qa

sudo yum-config-manager --add-repo https://download.opensuse.org/repositories/shells:fish:release:3/CentOS_7/shells:fish:release:3.repo
sudo yum install fish

curl https://sh.rustup.rs -sSf | sh
cargo install --locked bat fd-find ripgrep eza
