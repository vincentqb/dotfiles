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

" Automatically save before commands like :next and :make
set autowrite

" Activate spellchecker
set spell spelllang=en_us

function! PackInit() abort
    packadd minpac

    call minpac#init()
    call minpac#add('k-takata/minpac', {'type': 'opt'})
    call minpac#add('dracula/vim', { 'name': 'dracula' })

    call minpac#add('thinca/vim-visualstar')
    call minpac#add('ervandew/supertab')
    call minpac#add('AndrewRadev/linediff.vim')
    call minpac#add('tpope/vim-surround')
    call minpac#add('mbbill/undotree')
    call minpac#add('chrisbra/Recover.vim')
    " call minpac#add('christoomey/vim-tmux-navigator')

    call minpac#add('tpope/vim-dadbod')

    " call minpac#add('tpope/vim-fugitive')
    " call minpac#add('airblade/vim-gitgutter')
    call minpac#add('lewis6991/gitsigns.nvim')

    call minpac#add('psf/black')
    call minpac#add('neovim/nvim-lspconfig')
    call minpac#add('lervag/vimtex')

    call minpac#add('vimwiki/vimwiki')

endfunction

command! PackUpdate call PackInit() | call minpac#update()
command! PackClean  call PackInit() | call minpac#clean()
command! PackStatus packadd minpac | call minpac#status()

" Enable theme
" https://github.com/dracula/vim/issues/96
" let g:dracula_italic = 0
let g:dracula_colorterm = 0
colorscheme dracula

" Show undo tree with F5
nnoremap <F5> :UndotreeToggle<CR>

" Set default directory for vimwiki files
let g:vimwiki_list = [{'path': "~/wiki"}]
" Set vimwiki colors for each heading level: default is all same color
hi VimwikiHeader1 ctermfg=Green
hi VimwikiHeader2 ctermfg=Cyan
hi VimwikiHeader3 ctermfg=Blue
hi VimwikiHeader4 ctermfg=Yellow
hi VimwikiHeader5 ctermfg=Red
hi VimwikiHeader6 ctermfg=Brown

" Set vimtex
let g:tex_flavor = 'latex'
let g:vimtex_compiler_progname = 'nvr'
" https://github.com/lervag/vimtex/issues/1430
let g:vimtex_indent_on_ampersands = 0

" Language Server Protocol
lua << EOF

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
    on_attach=on_attach,
    settings={
        pylsp={
            plugins={
                -- pydocstyle={
                --     enabled=true,
                -- },
                flake8={
                    enabled=true,
                    maxLineLength=120,
                }
            }
        }
    }
}

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
