if status is-interactive
    # Commands to run in interactive sessions can go here
    # command -v nvm || nvm install lts > /dev/null

    # Point vim to nvim in userspace
    abbr v "nvim -O"
    abbr vi "nvim -O"
    abbr vim "nvim -O"
    abbr vimdiff "nvim -d"
    abbr view "nvim -RO"
    abbr s "kitty +kitten ssh"
    abbr icat "kitty +kitten icat"

    for motd in /run/motd.dynamic /etc/motd
        if test -e $motd
            cat $motd
        end
    end

end

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
if test -f /home/vincent/miniconda/bin/conda
    eval /home/vincent/miniconda/bin/conda "shell.fish" "hook" $argv | source
end
# <<< conda initialize <<<

