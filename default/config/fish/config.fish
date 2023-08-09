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
end
