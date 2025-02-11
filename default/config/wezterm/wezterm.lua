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
            name = "example1",
            -- proxy_command = { "ssh", "-T", "-A", "gpu1min", "wezterm", "cli", "proxy" },
            proxy_command = { "ssh", "-T", "-A", "gpu1min", "/home/ec2-user/.local/bin/wezterm-mux-server", "cli", "proxy" },
        },
    },
    ssh_domains = {
        {
            name = "example2",
            remote_address = "gpu1min",
            remote_wezterm_path = "/home/ec2-user/.local/bin/wezterm-mux-server",
        },
        {
            name = "example3",
            username = "ec2-user",
            -- IdentityFile = "~/.ssh/quennv_ec2.pem",
            remote_address = "ec2-54-166-254-8.compute-1.amazonaws.com",
            remote_wezterm_path = "/home/ec2-user/.local/bin/wezterm-mux-server",
        },
    -- or simply use:
    -- wezterm ssh gpu1min
    },
}
