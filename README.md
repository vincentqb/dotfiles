```
# Clone the repositories
git clone --recurse-submodules --remote-submodules --jobs 8 https://github.com/vincentqb/dotfiles ~/dotfiles
git submodule sync
git submodule update --init --recursive --remote

# Install python packages
/usr/bin/python3 -m ensurepip --user --upgrade
/usr/bin/python3 -m pip install --user --upgrade -r ~/dotfiles/requirements.txt

# Install dotfiles:
 PASSWD=github_application_password dot.py link default netrc

# Run corresponding install scripts:
# ~/dotfiles/install-macos.sh
# ~/dotfiles/install-amzn.sh
# ~/dotfiles/install-ubuntu.sh
~/dotfiles/install-fish.fish
```
