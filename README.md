Clone the repositories
```
git clone --recurse-submodules --remote-submodules --jobs 8 https://github.com/vincentqb/dotfiles ~/dotfiles
git submodule sync
git submodule update --init --recursive --remote
```
Run install scripts corresponding the environment
```
# ~/dotfiles/install-macos.sh
# ~/dotfiles/install-amzn.sh
# ~/dotfiles/install-ubuntu.sh
~/dotfiles/install-fish.fish
```
Install dotfiles
```
 PASSWD=github_application_password dot.py link default
```
The space prefix tells shell to forget command from history.
