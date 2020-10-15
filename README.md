# Installation

Install dependencies
```bash
pip install --user dotfiles black pylint flake8 isort neovim
```

Install dotfiles with [bashdot](https://github.com/bashdot/bashdot):
```
git submodule update --init --recursive
env GITHUB_NETRC_LOGIN=github_login GITHUB_NETRC_PASSWORD=github_application_password ~/dotfiles/bashdot/bashdot install default netrc
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
