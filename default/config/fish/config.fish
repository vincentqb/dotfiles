if status is-interactive
    # Commands to run in interactive sessions can go here
    # command -v nvm || nvm install lts > /dev/null

    # Point vim to nvim in userspace
    abbr v "nvim"
    abbr vi "nvim"
    abbr vim "nvim"
    abbr vimdiff "nvim -d"
    abbr view "nvim -R"
end
