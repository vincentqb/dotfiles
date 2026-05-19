#!/bin/sh
# Claude Code status line — mirrors the pure prompt style
# Reads JSON from stdin

input=$(cat)

user=$(whoami)
host=$(hostname -s)
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# Build cwd display: replace $HOME with ~
home="$HOME"
if [ -n "$cwd" ]; then
    display_cwd=$(echo "$cwd" | sed "s|^$home|~|")
else
    display_cwd=$(pwd | sed "s|^$home|~|")
fi

# Build context string
ctx_str=""
if [ -n "$used" ]; then
    ctx_str=" ctx:$(printf '%.0f' "$used")%"
fi

# Build model string
model_str=""
if [ -n "$model" ]; then
    model_str=" $model"
fi

printf "\033[1;32m%s\033[0m@\033[1;32m%s\033[0m  \033[1;34m%s\033[0m\033[0;33m%s\033[0m\033[0;36m%s\033[0m" \
    "$user" "$host" "$display_cwd" "$model_str" "$ctx_str"
