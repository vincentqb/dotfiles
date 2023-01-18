if status is-interactive
    # Commands to run in interactive sessions can go here
    command -v nvm || nvm install lts > /dev/null
end
