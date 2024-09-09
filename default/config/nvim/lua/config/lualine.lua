require('lualine').setup {
    options = {
        icons_enabled = false,
        theme = 'auto',
        globalstatus = true,
        component_separators = { left = '❯', right = '❮'},
        section_separators = { left = '', right = ''},
    },
    sections = {
        lualine_a = {},
        lualine_b = {'filename'},
        lualine_c = {'branch', 'diff', 'diagnostics'},
        lualine_x = {'encoding', 'fileformat', 'filetype'},
        lualine_y = {'progress'},
        lualine_z = {'location'}
    },
}
