# dotfiles

Install dotfiles with [bashdot](https://github.com/bashdot/bashdot):
```
git submodule update --init --recursive
env GITHUB_NETRC_LOGIN=github_login GITHUB_NETRC_PASSWORD=XXXX bashdot/bashdot install default
```

Shell: You can add the following to the end of your shell rc file to enable overriding:
```
if [ -f ~/.zshrc_local ]; then
    source ~/.zshrc_local
fi
```
If you’re using a different shell, you probably want to name the file differently.

Git: You can add the following to the end of your .gitconfig file to enable overriding:
```
[include]
        path = ~/.gitconfig_local
```

Vim: You can add the following to the end of your .vimrc file to enable overriding:
```
let $LOCALFILE=expand("~/.vimrc_local")
if filereadable($LOCALFILE)
    source $LOCALFILE
endif
```

tmux: You can add the following to the end of your .tmux.conf file to enable overriding4:
```
if-shell "[ -f ~/.tmux_local.conf ]" 'source ~/.tmux_local.conf'
```
