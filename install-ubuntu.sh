#!/bin/bash

git submodule sync
git submodule update --init --recursive
~/dotfiles/bashdot/bashdot install default

/usr/bin/pip3 install --user -r requirements.txt

# Install latest neovim
mkdir -p ~/.local/bin
wget https://github.com/neovim/neovim/releases/download/stable/nvim.appimage -O ~/.local/bin/nvim
chmod +x ~/.local/bin/nvim

# Update vim plugins
~/.local/bin/nvim +PackClean +qa
~/.local/bin/nvim +PackUpdate +qa

# https://launchpad.net/~fish-shell/+archive/ubuntu/release-3
sudo apt-add-repository ppa:fish-shell/release-3
sudo apt update
sudo apt install fish

sudo apt install tmux shellcheck texlive

~/.tmux/plugins/tpm/bin/update_plugins all	# prefix + U
~/.tmux/plugins/tpm/bin/clean_plugins	    # prefix + alt + u
~/.tmux/plugins/tpm/bin/install_plugins	    # prefix + I

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