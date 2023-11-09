" Specify Python 3 to use
let g:python3_host_prog = '/usr/bin/python3'
" Specify Python 2 to use
" let g:python_host_prog = '/usr/bin/python'

" Fold using indentation
au FileType python set foldmethod=indent foldnestmax=1 foldminlines=10
" Open/close folds with space
au FileType python nnoremap <space> za

" Automatic indentation
set smartindent
set breakindent
set breakindentopt=shift:2,min:40,sbr
set showbreak=>>

" Use spaces for tabs
set tabstop=4
set softtabstop=4
set shiftwidth=4
set expandtab

" Persistent undo tree, but careful about leaking sensitive information
set undofile

" Search and highlight while typing while ignoring case when only lower case used
set ignorecase
set smartcase

" Show matching brackets.
set showmatch

" Add vertical line to highlight column were row is too long
set colorcolumn=120

" Automatically save before commands like :next and :make
set autowrite

" Activate spellchecker
" set spell spelllang=en_us,programming
" Spell-check Markdown files and Git Commit Messages
" autocmd FileType markdown setlocal spell
" autocmd FileType gitcommit setlocal spell
" Disable spellcheck in python by default
" autocmd FileType python setlocal nospell
" Toggle spellchecking
map <F3> :setlocal spell! spelllang=en_us,programming<CR>

function! PackInit() abort
    packadd minpac

    call minpac#init()
    call minpac#add('k-takata/minpac', {'type': 'opt'})
    call minpac#add('dracula/vim', { 'name': 'dracula' })

    call minpac#add('thinca/vim-visualstar')
    " call minpac#add('ervandew/supertab')
    call minpac#add('AndrewRadev/linediff.vim')
    call minpac#add('tpope/vim-surround')
    call minpac#add('mbbill/undotree')
    call minpac#add('chrisbra/Recover.vim')
    " call minpac#add('christoomey/vim-tmux-navigator')

    call minpac#add('tpope/vim-dadbod')

    " call minpac#add('tpope/vim-fugitive')
    " call minpac#add('airblade/vim-gitgutter')
    call minpac#add('lewis6991/gitsigns.nvim')

    " call minpac#add('psf/black')
    call minpac#add('neovim/nvim-lspconfig')
    " call minpac#add('lervag/vimtex')

    " call minpac#add('vimwiki/vimwiki')
    " Run :DirtytalkUpdate manually
    " https://github.com/psliwka/vim-dirtytalk/issues/1
    " call minpac#add('psliwka/vim-dirtytalk', {'do': ':let &rtp = &rtp \| DirtytalkUpdate' })
    call minpac#add('psliwka/vim-dirtytalk', {'do': ':DirtytalkUpdate'})

endfunction

command! PackUpdate call PackInit() | call minpac#update()
command! PackClean  call PackInit() | call minpac#clean()
command! PackStatus packadd minpac | call minpac#status()

" Enable theme
" https://github.com/dracula/vim/issues/96
" let g:dracula_italic = 0
let g:dracula_colorterm = 0
colorscheme dracula

" Add horizontal line
" set cursorline
" highlight CursorLine ctermbg=lightgrey guibg=lightgrey
" highlight CursorLine ctermbg=black guibg=black

" Show undo tree with F5
nnoremap <F2> :UndotreeToggle<CR>

" Set vimtex
let g:tex_flavor = 'latex'
let g:vimtex_compiler_progname = 'nvr'
" https://github.com/lervag/vimtex/issues/1430
let g:vimtex_indent_on_ampersands = 0

" Make LSP messages appear above the current line
" https://github.com/neovim/nvim-lspconfig/issues/1046
" map <leader>d :lua vim.diagnostic.open_float(0, {scope="line"})<CR>
map <F7> :lua vim.diagnostic.open_float(0, {scope="line"})<CR>

" Language Server Protocol
lua << EOF

-- https://github.com/neovim/nvim-lspconfig

local lspconfig = require('lspconfig')

-- See: https://github.com/neovim/nvim-lspconfig/tree/54eb2a070a4f389b1be0f98070f81d23e2b1a715#suggested-configuration
local opts = { noremap=true, silent=true }
-- vim.keymap.set('n', '<space>e', vim.diagnostic.open_float, opts)
vim.keymap.set('n', '[d', vim.diagnostic.goto_prev, opts)
vim.keymap.set('n', ']d', vim.diagnostic.goto_next, opts)
-- vim.keymap.set('n', '<space>q', vim.diagnostic.setloclist, opts)

local ruff_format = function()
    print 'Workspace edit Ruff: Fix lint'
    vim.lsp.buf.format { async = true }
end

local ruff_organizeimports = function()
    vim.lsp.buf.execute_command({
        command = 'ruff.applyOrganizeImports',
        arguments = {{ uri = vim.uri_from_bufnr(0) }}
    })
end

local ruff_autofix = function()
    vim.lsp.buf.execute_command({
        command = 'ruff.applyAutofix',
        arguments = {{ uri = vim.uri_from_bufnr(0) }}
    })
end

local ruff_all = function()
    vim.lsp.buf.format { async = false }

    local params = { command = 'ruff.applyOrganizeImports', arguments = {{ uri = vim.uri_from_bufnr(0) }} }
    vim.lsp.buf_request_sync(0, 'workspace/executeCommand', params)

    local params = { command = 'ruff.applyAutofix', arguments = {{ uri = vim.uri_from_bufnr(0) }} }
    vim.lsp.buf_request_sync(0, 'workspace/executeCommand', params)

    print 'Ruff: Format, organize imports, autofix'
end

-- Use an on_attach function to only map the following keys
-- after the language server attaches to the current buffer
local on_attach = function(client, bufnr)
    -- Enable completion triggered by <c-x><c-o>
    vim.api.nvim_buf_set_option(bufnr, 'omnifunc', 'v:lua.vim.lsp.omnifunc')

    -- Mappings.
    -- See `:help vim.lsp.*` for documentation on any of the below functions
    local bufopts = { noremap=true, silent=true, buffer=bufnr }
    -- vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, bufopts)
    -- vim.keymap.set('n', 'gd', vim.lsp.buf.definition, bufopts)
    -- vim.keymap.set('n', 'K', vim.lsp.buf.hover, bufopts)
    -- vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, bufopts)
    -- vim.keymap.set('n', '<C-k>', vim.lsp.buf.signature_help, bufopts)
    -- vim.keymap.set('n', '<space>wa', vim.lsp.buf.add_workspace_folder, bufopts)
    -- vim.keymap.set('n', '<space>wr', vim.lsp.buf.remove_workspace_folder, bufopts)
    -- vim.keymap.set('n', '<space>wl', function()
    --     print(vim.inspect(vim.lsp.buf.list_workspace_folders()))
    -- end, bufopts)
    -- vim.keymap.set('n', '<space>D', vim.lsp.buf.type_definition, bufopts)
    -- vim.keymap.set('n', '<space>rn', vim.lsp.buf.rename, bufopts)
    -- vim.keymap.set('n', '<space>ca', vim.lsp.buf.code_action, bufopts)
    -- vim.keymap.set('n', '<F3>', vim.lsp.buf.code_action, bufopts)
    -- vim.keymap.set('n', 'gr', vim.lsp.buf.references, bufopts)
    vim.keymap.set('n', '<F4>', ruff_format, bufopts)
    vim.keymap.set('n', '<F5>', ruff_organizeimports, bufopts)
    vim.keymap.set('n', '<F6>', ruff_autofix, bufopts)
    vim.keymap.set('n', '<F7>', ruff_all, bufopts)
end

-- Configure `ruff-lsp`.
-- See: https://github.com/neovim/nvim-lspconfig/blob/master/doc/server_configurations.md#ruff_lsp
-- For the default config, along with instructions on how to customize the settings
lspconfig.ruff_lsp.setup {
    on_attach = on_attach,
    init_options = {
        settings = {
            -- Find with: echo $(/usr/bin/python3 -m site --user-base)/bin
            -- https://github.com/MasahiroSakoda/dotfiles/blob/1ff9351cbf7e861c1b1f8a4a33afefb244d827cc/home/dot_config/nvim/lua/lsp/servers/ruff_lsp.lua#L17
            -- path = {"/Users/quennv/Library/Python/3.9/bin/ruff"},
            interpreter = {"/usr/bin/python3"},
            -- Any extra CLI arguments for `ruff` go here.
            args = {
                -- "--extend-ignore", "E501",
                "--line-length", "120",
            },
            format = {
                args = {
                    "--line-length", "120",
                },
            },
        }
    }
}

-- https://github.com/python-lsp/python-lsp-server/blob/develop/CONFIGURATION.md
-- lspconfig.pylsp.setup{
--     on_attach=on_attach,
--     settings={
--         pylsp={
--             plugins={
--                 -- pydocstyle={
--                 --     enabled=true,
--                 -- },
--                 flake8={
--                     enabled=true,
--                     maxLineLength=120,
--                     -- see documentation for defaults
--                     ignore={'E24', 'W503', 'E226', 'E126', 'E704', 'E121', 'E123', 'W504', 'E203', 'E501'}
--                     -- TODO find a way to use extend-ignore instead
--                 }
--                 -- mypy={
--                 --     ignore_missing_imports=true
--                 -- }
--             }
--         }
--     }
-- }

-- https://github.com/neovim/nvim-lspconfig
-- require('lspconfig').pyright.setup{}

lspconfig.bashls.setup{on_attach=on_attach}
lspconfig.texlab.setup{on_attach=on_attach}
lspconfig.metals.setup{on_attach=on_attach}

-- local shfmt = require('lsp.diagnosticls.formatters.shfmt')
-- local shellcheck = require('lsp.diagnosticls.linters.shellcheck')

-- lspconfig.diagnosticls.setup {
--   on_attach=on_attach,
--   filetypes={ 'sh', 'yaml', 'lua' },
--   init_options={
--     filetypes={
--       sh='shellcheck',
--       yaml='yamllint',
--     },
--     formatFiletypes={
--       sh='shfmt',
--     },
--     formatters={
--       shfmt=shfmt,
--     },
--     linters={
--       shellcheck=shellcheck,
--     },
--   },
-- }

EOF
