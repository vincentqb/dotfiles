#!/bin/bash

git submodule sync
git submodule update --init --recursive

# Distro prereqs (things brew-on-Linux can't replace cleanly)
sudo apt update
sudo apt install -y build-essential curl ca-certificates git xsel kitty-terminfo shfmt

# Homebrew + everything in the Brewfile (formulae, cargo, uv tools)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
brew update
brew bundle

# Neovim plugins via lazy.nvim
nvim --headless "+Lazy! sync" +qa

# Fish as default shell
sudo chsh $USER -s $(which fish)

# Cargo + texlab (not in homebrew-core for Linux)
curl https://sh.rustup.rs -sSf | sh -s -- -y
~/.cargo/bin/cargo install --locked --git https://github.com/latex-lsp/texlab
~/.cargo/bin/cargo install-update -a
