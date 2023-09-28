Install dotfiles:
```
git clone --recurse-submodules --remote-submodules --jobs 8 https://github.com/vincentqb/dotfiles ~/dotfiles

git submodule sync
git submodule update --init --recursive --remote --merge --jobs 8
git pull --recurse-submodules

PASSWD=github_application_password \
    /usr/bin/python3 ~/dotfiles/pydot.py link default netrc

/usr/bin/python3 -m pip install --user --upgrade -r ~/dotfiles/requirements.txt
```

Alternatively, install dotfiles with [bashdot](https://github.com/bashdot/bashdot):
```
git clone https://github.com/bashdot/bashdot.git ~/bashdot/
PASSWD=github_application_password \
    ~/bashdot/bashdot install default netrc
```

Try zellij instead of tmux:
```
zellij --layout compact options --simplified-ui true --default-shell "fish" --default-mode "locked"
```

In neovim, don't forget to
```
:PackUpdate
:DirtytalkUpdate
```
