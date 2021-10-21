Install dotfiles with [bashdot](https://github.com/bashdot/bashdot):
```
git clone --recurse-submodules --remote-submodules --jobs 8 https://github.com/vincentqb/dotfiles ~/dotfiles

git submodule sync
git submodule update --init --recursive --remote --jobs 8
git pull --recurse-submodules

env PASSWD=github_application_password \
    ~/dotfiles/bashdot/bashdot install default netrc

/usr/bin/python3 -m pip install --user -r ~/dotfiles/requirements.txt
```
