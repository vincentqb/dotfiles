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
dot.py link default
 GITHUB=github_token OVERLEAF=overleaf_token dot.py link netrc
 ZULIP=zulip_api_key dot.py link zulip
```
The space prefix tells shell to forget command from history. Templates render
to `*.rendered` files, which are gitignored and get linked into `~`.

Transfer files from an SSH session (Ghostty)
```
# Install on BOTH the local computer and the remote host:
brew install trzsz-go

# Local, after linking these Fish dotfiles:
exec fish
s hostname

# Remote, at a shell prompt inside or outside tmux:
tsz ./report.pdf       # Download: choose a destination on the local computer.
trz                   # Upload: choose local files; save in the remote cwd.
tsz -d ./results/     # Download a directory.
trz -d                # Upload files or directories.
```
The `s` function wraps OpenSSH with [trzsz](https://trzsz.github.io/go), keeping
your SSH config and Ghostty's environment integration. It leaves automatic
terminfo installation disabled, matching the Ghostty config, and uses relay mode
for another SSH hop from a remote shell. Without `trzsz-go`, it falls back to
normal SSH.

Transfers use the wrapped terminal connection and work through remote tmux.
Run the transfer command in a tmux shell pane. An existing plain SSH connection
needs one reconnect with `s`: detach tmux (`Ctrl-Q`, then `d`), reconnect, and
run `tmux attach`; the tmux session and its programs keep running.

Transfer files over an existing SSH connection (Kitty)
```
# Local, in Kitty:
kitty +kitten ssh hostname

# Remote, outside tmux:
kitten transfer ./report.pdf Downloads/
kitten transfer --direction=upload Downloads/input.csv ./
```
These commands use the terminal connection. `Downloads/` refers to
`~/Downloads/` on the local computer; `./` refers to the remote shell's working
directory.
Avoid an unquoted `~/` for local paths: the remote shell would expand it.
Kitty asks for approval on the local computer and can also transfer directories.

With the installed tmux 3.8 and kitten 0.44, detach tmux first (`Ctrl-Q`, then
`d`) and run `tmux attach` afterward. The transfer protocol is not forwarded by
this combination, even with `allow-passthrough on`.

If a host's preinstalled `kitten` reports a glibc version error, use the portable
copy from Kitty's SSH bootstrap when it is present. In Fish:
```
set -l k ~/.local/share/kitty-ssh-kitten/kitty/bin/kitten
$k transfer ./report.pdf Downloads/
$k transfer --direction=upload Downloads/input.csv ./
```
