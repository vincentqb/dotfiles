function codex-resume --description 'Replay a codex launch line, resuming the newest thread of this directory instead of starting a new one'
    # tmux-resurrect relaunches codex panes through this: its rule
    # "~codex->codex-resume *" hands over the flags the pane's codex was started
    # with (see tmux3/tmux.conf). A bare `codex resume --last` keeps the
    # conversation but not the rail or the model: the provider comes from config
    # layering (Mantle unless codex-byoa's -c override is on the line) and the
    # model from the profile default, so an astra session came back as sol
    # (observed 2026-10-17). Replaying the original flags keeps both.
    #
    # Everything from a `resume` subcommand onward is dropped and replaced by
    # `resume --last`, so a pane that was itself a resume (picker or --last)
    # comes back resumed too and the subcommand is never doubled. Flags that
    # followed `resume` (--cd, --sandbox, ...) are lost; tmux restores the
    # directory anyway.
    set -l flags $argv
    set -l at (contains -i -- resume $flags)
    if test -n "$at"
        set -e flags[$at..-1]
    end
    command codex $flags resume --last
end
