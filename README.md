# Installation

Install dependencies
```bash
pip install --user dotfiles black pylint flake8 isort neovim
```

Install dotfiles with [dotfiles](https://github.com/jbernard/dotfiles):
```bash
git submodule update --init --recursive
~/dotfiles/dotfiles/bin/dotfiles --sync
```

# Maintenance

### tmux
* update plugins: prefix + U
* install new plugins: prefix + I
* uninstall unused plugins: prefix + alt + u

### zsh
* zgen selfupdate
* zgen reset
* zgen update

### vim
* :PlugUpgrade
* :PlugClean
* :PlugUpdate
