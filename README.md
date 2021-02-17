Install dotfiles with [bashdot](https://github.com/bashdot/bashdot):
```
pip install --user -r requirements.txt

git clone --recurse-submodules --remote-submodules -j8 https://github.com/vincentqb/dotfiles ~/dotfiles
git submodule update --init --recursive

PASSWD=github_application_password \
    ~/dotfiles/bashdot/bashdot install default netrc
```
