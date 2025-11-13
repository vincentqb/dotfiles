```
# Clone the repositories
git clone --recurse-submodules --remote-submodules --jobs 8 https://github.com/vincentqb/dotfiles ~/dotfiles
git submodule sync
git submodule update --init --recursive --remote

# Install python packages
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install -r requirements.txt

# Install dotfiles (space prefix tells shell to forget command in history)
 PASSWD=github_application_password uvx --python 3.9 --from dot-py dot.py link default

# Run corresponding install scripts:
# ~/dotfiles/install-macos.sh
# ~/dotfiles/install-amzn.sh
# ~/dotfiles/install-ubuntu.sh
~/dotfiles/install-fish.fish
```
