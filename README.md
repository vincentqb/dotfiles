Install dotfiles with [bashdot](https://github.com/bashdot/bashdot):
```
git clone --recurse-submodules --remote-submodules --jobs 8 https://github.com/vincentqb/dotfiles ~/dotfiles

git submodule sync
git submodule update --init --recursive --remote --jobs 8

env PASSWD=github_application_password \
    ~/dotfiles/bashdot/bashdot install default netrc

pip install --user -r requirements.txt
```
