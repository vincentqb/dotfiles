function s --wraps=ssh --description "SSH with in-session file transfers"
    if not command -q trzsz
        # Keep Ghostty's normal ssh function until trzsz-go is installed.
        ssh $argv
        return
    end

    set -l ssh_command ssh
    set -l transfer_flags
    if set -q SSH_CONNECTION
        # On a jump host, the laptop's wrapper owns the file picker.
        set -a transfer_flags --relay
    end

    if set -q GHOSTTY_BIN_DIR; and test -x "$GHOSTTY_BIN_DIR/ghostty"; and "$GHOSTTY_BIN_DIR/ghostty" +ssh --help >/dev/null 2>&1
        # Preserve ssh-env integration. Automatic terminfo upload stays off,
        # matching ghostty/config: RequestTTY force can make that upload hang.
        set ssh_command "$GHOSTTY_BIN_DIR/ghostty" +ssh --terminfo=false --
    else if test "$TERM" = xterm-ghostty; or test "$TERM_PROGRAM" = ghostty
        # Older Ghostty builds lack +ssh. Use its portable TERM fallback and
        # environment forwarding without changing the host's SSH settings.
        set --function --export TERM xterm-256color
        set -a ssh_command -o SendEnv=COLORTERM -o SendEnv=TERM_PROGRAM -o SendEnv=TERM_PROGRAM_VERSION
    end

    command trzsz $transfer_flags $ssh_command $argv
end
