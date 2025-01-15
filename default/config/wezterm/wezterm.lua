local wezterm = require 'wezterm'

return {
    -- default_prog = { '/usr/local/bin/fish', '-l' }
    default_prog = { '/opt/homebrew/bin/fish', '-l' },
    font = wezterm.font 'Menlo',
    -- font = wezterm.font 'Fira Code',
    -- font = wezterm.font 'JetBrains Mono',
    font_size = 14.0,
    color_scheme = "Dracula (Official)",
    tab_bar_at_bottom = true,
    hide_tab_bar_if_only_one_tab = true,
    use_fancy_tab_bar = false,
    window_decorations = "TITLE | RESIZE",
    unix_domains = {
        {
            name = "example",
            proxy_command = { "ssh", "-T", "-A", "gpu1min", "wezterm", "cli", "proxy" },
        },
    },
}
