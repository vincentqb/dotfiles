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
alias finch='sudo HOME=/home/quennv DOCKER_CONFIG=/home/quennv/.docker finch'

# Keep Amazon toolbox builds ahead of Homebrew on PATH.
#
# fish_user_paths (universal, in gitignored fish_variables) had linuxbrew
# before ~/.toolbox/bin, so `codex` resolved to the stale public Homebrew
# cask (0.144.x) instead of the ASBX Codex-on-Bedrock build. The public
# build's /model picker never learns about new Bedrock models (GPT-5.6
# family, GPT-6-Astra): the model catalog ships with each internal release
# and is fetched per client version. claude/kiro-cli are toolbox-only, but
# toolbox-first protects them from future brew-installed shadows too.
# zsh already ends with `export PATH=$HOME/.toolbox/bin:$PATH`; this is the
# fish equivalent, run at every shell start so brew reordering can't
# regress it. (fish_user_paths itself was also reordered, but that file is
# not tracked, hence this belt-and-suspenders line.)
fish_add_path --global --move --path ~/.toolbox/bin
