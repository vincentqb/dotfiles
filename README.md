Install dotfiles with [bashdot](https://github.com/bashdot/bashdot):
```
git clone --recurse-submodules --remote-submodules --jobs 8 https://github.com/vincentqb/dotfiles ~/dotfiles

git submodule sync
git submodule update --init --recursive --remote --merge --jobs 8
git pull --recurse-submodules

PASSWD=github_application_password \
    ~/dotfiles/bashdot/bashdot install default netrc

/usr/bin/python3 -m pip install --user -r ~/dotfiles/requirements.txt
```

Try zellij in place of tmux:
```
# wget -qO- https://github.com/zellij-org/zellij/releases/download/latest/zellij-x86_64-unknown-linux-musl.tar.gz | tar xvpz
wget -qO- https://github.com/zellij-org/zellij/releases/download/latest/zellij-aarch64-apple-darwin.tar.gz | tar xvpz
./zellij --layout compact options --simplified-ui true
```
