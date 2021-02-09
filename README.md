Install dotfiles with [bashdot](https://github.com/bashdot/bashdot):
```
git clone --recurse-submodules --remote-submodules -j8 https://github.com/vincentqb/dotfiles ~/dotfiles
git submodule update --init --recursive
env PASSWD=github_application_password \
    ~/dotfiles/bashdot/bashdot install default netrc
```
