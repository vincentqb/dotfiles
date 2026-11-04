# Keep Fish's native Git completions, including its handling of global options.
if status get-file completions/git.fish >/dev/null 2>&1
    status get-file completions/git.fish | source
else
    source "$__fish_data_dir/completions/git.fish"
    or return
end

functions -q __fish_git; or return
functions --erase _dotfiles_git_query
functions --copy __fish_git _dotfiles_git_query

function __fish_git
    if contains -- ls-files $argv; and contains -- -o $argv; and contains -- --exclude-standard $argv
        # Leave Git's explicit pathspec modes to the native implementation.
        if string match -qr '^--(literal|glob|noglob)-pathspecs$' -- (commandline -xpc); or set -q GIT_LITERAL_PATHSPECS; or set -q GIT_GLOB_PATHSPECS; or set -q GIT_NOGLOB_PATHSPECS
            _dotfiles_git_query $argv
            return $status
        end
        set -l token (commandline -xct)
        if test (count $token) -le 1; and not string match -qr '^[:/]' -- "$token"
            # Scan the current token's directory, offering whole new folders.
            # ?* excludes the directory itself so Tab can descend into it.
            set -l directory (string replace -r '[^/]*$' '' -- "$token")
            # Escape Git glob characters, preserving ./ and ../ path semantics.
            set -l pathspec (string replace -ra '([*?\[\]\\\\])' '\\\\$1' -- "$directory")'?*'
            _dotfiles_git_query $argv --directory --no-empty-directory -- "$pathspec"
            return $status
        end
    end
    _dotfiles_git_query $argv
end
