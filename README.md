Install dotfiles:
```
git clone --recurse-submodules --remote-submodules --jobs 8 https://github.com/vincentqb/dotfiles ~/dotfiles

git submodule sync
git submodule update --init --recursive --remote

 PASSWD=github_application_password ~/dotfiles/dotpy/dotpy link default netrc
```
Install python packages:
```
/usr/bin/python3 -m ensurepip --user --upgrade
/usr/bin/python3 -m pip install --user --upgrade -r ~/dotfiles/requirements.txt
```
