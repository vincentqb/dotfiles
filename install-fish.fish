#!/usr/bin/fish

# Extend $PATH
fish_add_path $HOME/bin $HOME/.local/bin
fish_add_path $HOME/homebrew/bin $HOME/homebrew/sbin /opt/homebrew/bin
fish_add_path $HOME/.toolbox/bin
fish_add_path $HOME/.cargo/bin
fish_add_path $(/usr/bin/python3 -m site --user-base)/bin

# Install plugin manager
curl -sL https://git.io/fisher | source; and fisher install jorgebucaran/fisher

# Configure prompt
# fish_config prompt choose terlar
# fisher install dracula/fish
fisher install acomagu/fish-async-prompt
fisher install pure-fish/pure
set -U async_prompt_functions _pure_prompt_git

# https://github.com/wez/wezterm/issues/1846
# fisher install danhper/fish-ssh-agent

# Return to default keybindings
fish_default_key_bindings
rm -f ~/.config/fish/functions/fish_user_key_bindings.fish

# Set vim keybindings
# fish_vi_key_bindings

# Enable CTRL+F to accept autocomplete
# https://github.com/fish-shell/fish-shell/issues/3541
# function fish_user_key_bindings
#     for mode in insert default visual
#         bind -M $mode \cf forward-char
#     end
# end
# funcsave fish_user_key_bindings

# Set nvim as default editor
set -Ux EDITOR nvim
set -Ux VISUAL nvim
set -Ux TEXEDIT "nvim %s"
set -Ux GIT_EDITOR nvim

# eza - Color Scheme Definitions
# https://github.com/dracula/exa/blob/main/exa_colors.zshrc
set -Ux EZA_COLORS "\
uu=36:\
gu=37:\
sn=32:\
sb=32:\
da=34:\
ur=34:\
uw=35:\
ux=36:\
ue=36:\
gr=34:\
gw=35:\
gx=36:\
tr=34:\
tw=35:\
tx=36:"
# https://github.com/DarrinTisdale/zsh-aliases-exa/blob/master/zsh-aliases-exa.plugin.zsh
# alias lz="eza -lm --no-user --no-permissions --time-style long-iso -s modified -r --grid --color=always"
# funcsave lz

# Combine autossh with tmux to get a persistent ssh connection
# https://jeffmcneill.com/autossh/
# https://pempek.net/articles/2013/04/24/vpn-less-persistent-ssh-sessions/
# https://derpops.bike/computers/2014/09/05/persistent-ssh-connections-with-context.html
# https://coderwall.com/p/aohfrg/smux-ssh-with-auto-reconnect-tmux-a-mosh-replacement
# alias ssa="AUTOSSH_FIRST_POLL=5 AUTOSSH_POLL=5 autossh -M $(awk 'BEGIN { srand(); do r = rand()*32000; while ( r < 20000 ); printf("%d\n",r)  }' < /dev/null)"
# alias ssa='AUTOSSH_FIRST_POLL=5 AUTOSSH_POLL=5 autossh -M $(/usr/bin/python3 -c "import random; print(random.randrange(20_000, 30_000));")'
# https://unix.stackexchange.com/questions/275681/ssh-connection-through-ssh-tunnel-keeps-closing
# alias ssa='AUTOSSH_FIRST_POLL=5 AUTOSSH_POLL=5 autossh -M 0'
# funcsave ssa

# cp with progress bar
# alias pcp="rsync -ahrz --info=progress2"
# funcsave pcp

# Configure node.js to launch language servers
# fisher install jorgebucaran/nvm.fish
# nvm install lts
# npm install -g bash-language-server
# npm install -g diagnostic-languageserver
# npm install -g neovim yarn
# yarn global add neovim

# Set up anaconda in fish
# conda init fish
# conda config --set changeps1 False
