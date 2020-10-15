Install dotfiles with [bashdot](https://github.com/bashdot/bashdot):
```
git submodule update --init --recursive
env GITHUB_LOGIN=github_login \
    GITHUB_PASSWORD=github_application_password \
    ~/dotfiles/bashdot/bashdot install default netrc
```
