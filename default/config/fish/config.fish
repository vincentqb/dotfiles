if status is-interactive
    # Commands to run in interactive sessions can go here
    # command -v nvm || nvm install lts > /dev/null

    # Point vim to nvim in userspace
    # abbr v "nvim -O"
    # abbr vi "nvim -O"
    abbr vim "nvim -O"
    abbr vimdiff "nvim -d"
    # abbr view "nvim -RO"
    abbr s "kitty +kitten ssh"
    abbr icat "kitty +kitten icat"
    abbr lz "eza -lm --no-user --no-permissions --time-style long-iso -s modified -r --grid --color=always"
    abbr pcp "rsync -ahrz --info=progress2"
    abbr ssa "AUTOSSH_FIRST_POLL=5 AUTOSSH_POLL=5 autossh -M 0"

    # Incompatible with wezterm-mux-server
    # for motd in /run/motd.dynamic /etc/motd
    #     if test -e $motd
    #         cat $motd
    #     end
    # end

end

set -gx CLAUDE_CODE_USE_BEDROCK "1"

# Pure prompt overrides (these plugin-provided defaults live in a gitignored
# conf.d, so override them here in the tracked config instead of editing the
# plugin file).
set -g pure_show_exit_status true
set -g pure_separate_prompt_on_error true

# >>> vscode python
if set -q VSCODE_FISH_ACTIVATE
    eval $VSCODE_FISH_ACTIVATE
end
# <<< vscode python

# Added by AIM CLI
set -gx PATH "/local/home/quennv/.aim/mcp-servers" $PATH
