# dotfiles

Install dotfiles with [bashdot](https://github.com/bashdot/bashdot):
```
git submodule update --init --recursive
env GITHUB_NETRC_LOGIN=github_login GITHUB_NETRC_PASSWORD=github_application_password ~/dotfiles/bashdot/bashdot install default netrc
```

Install dotfiles with [dotfiles](https://github.com/jbernard/dotfiles):
```
git submodule update --init --recursive
~/dotfiles/dotfiles/bin/dotfiles --sync
```
