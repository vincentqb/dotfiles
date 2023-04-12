#!/usr/bin/fish

# Extend $PATH
fish_add_path $HOME/bin $HOME/.local/bin $HOME/homebrew/bin $HOME/homebrew/sbin /opt/homebrew/bin $HOME/.toolbox/bin $HOME/.cargo/bin

# Install plugin manager
curl -sL https://git.io/fisher | source; and fisher install jorgebucaran/fisher

# Configure prompt
# fish_config prompt choose terlar
# fisher install dracula/fish
fisher install acomagu/fish-async-prompt
fisher install pure-fish/pure
set -U async_prompt_functions _pure_prompt_git

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

# Combine autossh with tmux to get a persistent ssh connection
# https://jeffmcneill.com/autossh/
# https://pempek.net/articles/2013/04/24/vpn-less-persistent-ssh-sessions/
# https://derpops.bike/computers/2014/09/05/persistent-ssh-connections-with-context.html
# https://coderwall.com/p/aohfrg/smux-ssh-with-auto-reconnect-tmux-a-mosh-replacement
# alias ssa="AUTOSSH_FIRST_POLL=5 AUTOSSH_POLL=5 autossh -M $(awk 'BEGIN { srand(); do r = rand()*32000; while ( r < 20000 ); printf("%d\n",r)  }' < /dev/null)"
# alias ssa='AUTOSSH_FIRST_POLL=5 AUTOSSH_POLL=5 autossh -M $(/usr/bin/python3 -c "import random; print(random.randrange(20_000, 30_000));")'
# https://unix.stackexchange.com/questions/275681/ssh-connection-through-ssh-tunnel-keeps-closing
alias ssa='AUTOSSH_FIRST_POLL=5 AUTOSSH_POLL=5 autossh -M 0'
funcsave ssa

# cp with progress bar
alias pcp="rsync -a --info=progress2"
funcsave pcp

# Configure node.js to launch language servers

# Set up anaconda in fish
conda init fish
conda config --set changeps1 False
