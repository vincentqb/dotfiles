-- Activate spellchecker
vim.opt.spell = true
vim.opt.spelllang = { 'en_us' }

-- Specify Python 3 to use
vim.g.python3_host_prog = '/usr/bin/python3'
-- Specify Python 2 to use
vim.g.python_host_prog = '/usr/bin/python'

-- Fold using indentation
vim.cmd([[
	au FileType python set foldmethod=indent foldnestmax=1 foldminlines=10
	au FileType python nnoremap <space> za
]])

-- Automatic indentation
vim.opt.smartindent = true
vim.opt.breakindent = true
vim.opt.breakindentopt = "shift:2,min:40,sbr"
vim.opt.showbreak = ">>"

-- Persistent undo tree, but careful about leaking sensitive information
vim.opt.undofile = true

-- Search and highlight while typing while ignoring case when only lower case used
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.incsearch = true
vim.opt.hlsearch = true

-- Use spaces for tabs
vim.opt.tabstop = 4
vim.opt.softtabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true

-- Show matching brackets.
vim.opt.showmatch = true

-- Automatically save before commands like :next and :make
vim.opt.autowrite = true

-- https://dev.to/vonheikemen/creating-a-lua-interface-for-minpac-1jd2
function PackInit()
    vim.cmd('packadd minpac')

    vim.call('minpac#init')
    local add = vim.fn['minpac#add']

    add('k-takata/minpac', {type = 'opt'})
    add('dracula/vim', {name = 'dracula' })

    add('thinca/vim-visualstar')
    add('ervandew/supertab')
    add('AndrewRadev/linediff.vim')
    add('tpope/vim-surround')
    add('mbbill/undotree')
    add('chrisbra/Recover.vim')
    -- add('christoomey/vim-tmux-navigator')

    add('tpope/vim-dadbod')

    -- add('tpope/vim-fugitive')
    -- add('airblade/vim-gitgutter')
    add('lewis6991/gitsigns.nvim')

    add('psf/black')
    add('neovim/nvim-lspconfig')
    add('lervag/vimtex')

    add('vimwiki/vimwiki')

end

-- Define user commands for updating/cleaning the plugins.
-- Each of them calls PackInit() to load minpac and register
-- the information of plugins, then performs the task.
vim.cmd [[
  command! PackUpdate lua PackInit(); vim.call('minpac#update')
  command! PackClean  lua PackInit(); vim.call('minpac#clean')
  command! PackStatus lua PackInit(); vim.call('minpac#status')
]]

-- Enable theme
-- https://github.com/dracula/vim/issues/96
vim.g.dracula_italic = 0
vim.g.dracula_colorterm = 0
vim.cmd([[colorscheme dracula]])

-- Show undo tree with F5
vim.api.nvim_set_keymap("n", "<F5>", ":UndotreeToggle<CR>", { noremap = true })

-- Set default directory for vimwiki files
vim.g.vimwiki_list = {{path = '~/Docs/Mywiki', syntax = 'markdown', ext = '.md'}}

-- Set vimwiki colors for each heading level: default is all same color
vim.highlight.create('ColorColumn', {ctermfg='Green'}, false)
vim.highlight.create('VimwikiHeader1', {ctermfg='Green'}, false)
vim.highlight.create('VimwikiHeader2', {ctermfg='Cyan'}, false)
vim.highlight.create('VimwikiHeader3', {ctermfg='Blue'}, false)
vim.highlight.create('VimwikiHeader4', {ctermfg='Yellow'}, false)
vim.highlight.create('VimwikiHeader5', {ctermfg='Red'}, false)
vim.highlight.create('VimwikiHeader6', {ctermfg='Brown'}, false)

-- Set vimtex
vim.g.tex_flavor = 'latex'
vim.g.vimtex_compiler_progname = 'nvr'
-- https://github.com/lervag/vimtex/issues/1430
vim.g.vimtex_indent_on_ampersands = 0

-- Language Server Protocol

-- https://github.com/neovim/nvim-lspconfig
local on_attach = function(_, bufnr)

    local function buf_set_keymap(...) vim.api.nvim_buf_set_keymap(bufnr, ...) end
    local function buf_set_option(...) vim.api.nvim_buf_set_option(bufnr, ...) end

    -- Enable completion triggered by <c-x><c-o>
    buf_set_option('omnifunc', 'v:lua.vim.lsp.omnifunc')

end

local lspconfig = require('lspconfig')

-- https://github.com/python-lsp/python-lsp-server/blob/develop/CONFIGURATION.md
lspconfig.pylsp.setup{
    on_attach = on_attach,
    settings = {
        pylsp = {
            plugins = {
                -- pydocstyle = {
                --     enabled = true,
                -- },
                flake8 = {
                    enabled = true,
                    maxLineLength = 120,
                }
            }
        }
    }
}

-- https://github.com/neovim/nvim-lspconfig
-- require('lspconfig').pyright.setup{}

lspconfig.bashls.setup{on_attach = on_attach}
lspconfig.texlab.setup{on_attach = on_attach}
lspconfig.metals.setup{on_attach = on_attach}

-- local shfmt = require('lsp.diagnosticls.formatters.shfmt')
-- local shellcheck = require('lsp.diagnosticls.linters.shellcheck')

-- lspconfig.diagnosticls.setup {
--   on_attach = on_attach,
--   filetypes = { 'sh', 'yaml', 'lua' },
--   init_options = {
--     filetypes = {
--       sh = 'shellcheck',
--       yaml = 'yamllint',
--     },
--     formatFiletypes = {
--       sh = 'shfmt',
--     },
--     formatters = {
--       shfmt = shfmt,
--     },
--     linters = {
--       shellcheck = shellcheck,
--     },
--   },
-- }
