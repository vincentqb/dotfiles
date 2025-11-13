#!/bin/bash

git submodule sync
git submodule update --init --recursive

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install -r requirements.txt

# Install latest neovim
sudo apt -y install libfuse2
mkdir -p ~/.local/bin
wget https://github.com/neovim/neovim/releases/download/stable/nvim-linux-x86_64.appimage -O ~/.local/bin/nvim
chmod +x ~/.local/bin/nvim
sudo apt -y install python3-pynvim python3-neovim
# Update nvim plugins
~/.local/bin/nvim --headless +PackClean +qa
~/.local/bin/nvim --headless +PackUpdate +qa
~/.local/bin/nvim --headless +DirtytalkUpdate +qa

# https://github.com/kiyoon/tmux-appimage
curl -s https://api.github.com/repos/kiyoon/tmux-appimage/releases/latest \
| grep "browser_download_url.*appimage" \
| cut -d : -f 2,3 \
| tr -d \" \
| wget -qi - \
&& chmod +x tmux.appimage && mv ./tmux.appimage ~/.local/bin/tmux

sudo apt -y install tmux shellcheck texlive node

~/.tmux/plugins/tpm/bin/update_plugins all	# prefix + U
~/.tmux/plugins/tpm/bin/clean_plugins	    # prefix + alt + u
~/.tmux/plugins/tpm/bin/install_plugins	    # prefix + I

# Install zellij to use instead of tmux
mkdir -p ~/.local/bin
wget -qO- https://github.com/zellij-org/zellij/releases/download/v0.34.4/zellij-x86_64-unknown-linux-musl.tar.gz | tar xvpz -C ~/.local/bin
# Install on remote ssh host
# https://sw.kovidgoyal.net/kitty/faq/#i-get-errors-about-the-terminal-being-unknown-or-opening-the-terminal-failing-or-functional-keys-like-arrow-keys-don-t-work
sudo apt install kitty-terminfo

# Install latest nodejs
# https://github.com/bash-lsp/bash-language-server/issues/428#issuecomment-1147740945
curl -fsSL https://deb.nodesource.com/setup_current.x | sudo -E bash -
sudo apt install -y nodejs
# bashls
# sudo snap install bash-language-server --classic
sudo npm i -g bash-language-server
sudo apt install -y shfmt shellcheck

# scala
# curl -fLo cs https://git.io/coursier-cli-"$(uname | tr LD ld)"
# chmod +x cs
# ./cs install metals
# export PATH="$PATH:/home/ubuntu/.local/share/coursier/bin"\

# Install anaconda
# wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
# bash ~/miniconda.sh -b -p ~/miniconda
# eval "$(~/miniconda/bin/conda shell.bash hook)"
# source ~/miniconda/bin/activate
# conda init zsh
# conda init fish
# conda config --set auto_activate_base true
# conda config --set changeps1 False
# conda update -n base -c conda-forge conda

# sudo apt -y install fdfind bat ripgrep
curl https://sh.rustup.rs -sSf | sh -s -- -y
~/.cargo/bin/cargo install --locked bat fd-find ripgrep eza
~/.cargo/bin/cargo install --locked --git https://github.com/latex-lsp/texlab

# zenith
sudo apt install curl
curl -sL https://raw.githubusercontent.com/wimpysworld/deb-get/main/deb-get | sudo -E bash -s install deb-get
deb-get install zenith
deb-get update
deb-get upgrade

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# cat requirements.in | xargs --max-lines=1 uv tool install

# Install dotfiles
uv tool run --from dot-py dot.py link default

# https://launchpad.net/~fish-shell/+archive/ubuntu/release-3
sudo apt-add-repository ppa:fish-shell/release-4
sudo apt update
sudo apt -y install fish
sudo chsh ubuntu -s /usr/bin/fish
