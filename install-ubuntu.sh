#!/bin/bash

git submodule sync
git submodule update --init --recursive
~/dotfiles/dot.py/dot.py link default

/usr/bin/python3 -m pip install --upgrade pip
/usr/bin/python3 -m pip install --user -r requirements.txt

# Install latest neovim
sudo apt -y install libfuse2
mkdir -p ~/.local/bin
wget https://github.com/neovim/neovim/releases/download/stable/nvim.appimage -O ~/.local/bin/nvim
chmod +x ~/.local/bin/nvim
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

# https://launchpad.net/~fish-shell/+archive/ubuntu/release-3
sudo apt-add-repository ppa:fish-shell/release-3
sudo apt update
sudo apt -y install fish

sudo apt -y install tmux shellcheck texlive node

~/.tmux/plugins/tpm/bin/update_plugins all	# prefix + U
~/.tmux/plugins/tpm/bin/clean_plugins	    # prefix + alt + u
~/.tmux/plugins/tpm/bin/install_plugins	    # prefix + I

# Install zellij to use instead of tmux
mkdir -p ~/.local/bin
wget -qO- https://github.com/zellij-org/zellij/releases/download/v0.34.4/zellij-x86_64-unknown-linux-musl.tar.gz | tar xvpz -C ~/.local/bin

# bashls
# sudo snap install bash-language-server

# scala
# curl -fLo cs https://git.io/coursier-cli-"$(uname | tr LD ld)"
# chmod +x cs
# ./cs install metals
# export PATH="$PATH:/home/ubuntu/.local/share/coursier/bin"\

# Install anaconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p ~/miniconda
eval "$(~/miniconda/bin/conda shell.bash hook)"
source ~/miniconda/bin/activate
conda init zsh
conda init fish
conda config --set auto_activate_base true
conda update -n base -c conda-forge conda

# sudo apt -y install fdfind bat ripgrep
curl https://sh.rustup.rs -sSf | sh -s -- -y
~/.cargo/bin/cargo install --locked bat fd-find ripgrep eza
cargo install --locked --git https://github.com/latex-lsp/texlab
