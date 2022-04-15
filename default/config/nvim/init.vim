" set runtimepath^=~/.vim runtimepath+=~/.vim/after
" let &packpath = &runtimepath
" source ~/.vimrc

if &compatible
  " `:set nocp` has many side effects. Therefore this should be done
  " only when 'compatible' is set.
  set nocompatible
endif

runtime! common.vim
runtime! plugin/sensible.vim

function! PackInit() abort
    packadd minpac

    call minpac#init()
    call minpac#add('k-takata/minpac', {'type': 'opt'})
    call minpac#add('tpope/vim-sensible')
    call minpac#add('dracula/vim', { 'name': 'dracula' })

    call minpac#add('thinca/vim-visualstar')
    call minpac#add('ervandew/supertab')
    call minpac#add('AndrewRadev/linediff.vim')
    call minpac#add('tpope/vim-surround')
    call minpac#add('mbbill/undotree')
    call minpac#add('chrisbra/Recover.vim')
    call minpac#add('christoomey/vim-tmux-navigator')

    call minpac#add('tpope/vim-dadbod')

    call minpac#add('tpope/vim-fugitive')
    call minpac#add('airblade/vim-gitgutter')

    call minpac#add('psf/black')
    call minpac#add('neovim/nvim-lspconfig')
    call minpac#add('williamboman/nvim-lsp-installer')
    call minpac#add('lervag/vimtex')
    " call minpac#add('tmhedberg/SimpylFold')

    call minpac#add('vimwiki/vimwiki')

endfunction

command! PackUpdate call PackInit() | call minpac#update()
command! PackClean  call PackInit() | call minpac#clean()
command! PackStatus packadd minpac | call minpac#status()

syntax enable
colorscheme dracula

" Set default directory for vimwiki files
let g:vimwiki_list = [{'path': "~/wiki"}]

" Set vimwiki colors for each heading level: default is all same color
hi VimwikiHeader1 ctermfg=Green
hi VimwikiHeader2 ctermfg=Cyan
hi VimwikiHeader3 ctermfg=Blue
hi VimwikiHeader4 ctermfg=Yellow
hi VimwikiHeader5 ctermfg=Red
hi VimwikiHeader6 ctermfg=Brown

" Specify python to use in nvim
" Python 3
let g:python3_host_prog='/usr/bin/python3'
" Python 2
let g:python_host_prog='/usr/bin/python'

let g:tex_flavor = 'latex'
let g:vimtex_compiler_progname = 'nvr'
" https://github.com/lervag/vimtex/issues/1430
let g:vimtex_indent_on_ampersands = 0

" Languange Server Protocol
lua << EOF


local lspconfig = require('lspconfig')
local on_attach = function(_, bufnr)

  local function buf_set_keymap(...) vim.api.nvim_buf_set_keymap(bufnr, ...) end
  local function buf_set_option(...) vim.api.nvim_buf_set_option(bufnr, ...) end

  -- Enable completion triggered by <c-x><c-o>
  buf_set_option('omnifunc', 'v:lua.vim.lsp.omnifunc')

end

local lsp_installer = require("nvim-lsp-installer")

-- https://github.com/python-lsp/python-lsp-server/blob/develop/CONFIGURATION.md
lspconfig.pylsp.setup{
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

lspconfig.bashls.setup{}
lspconfig.texlab.setup{}
lspconfig.metals.setup{}

local shfmt = require 'lsp.diagnosticls.formatters.shfmt'
local shellcheck = require 'lsp.diagnosticls.linters.shellcheck'

lspconfig.diagnosticls.setup {
  on_attach = on_attach,
  filetypes = { 'sh', 'yaml', 'lua' },
  init_options = {
    filetypes = {
      sh = 'shellcheck',
      yaml = 'yamllint',
    },
    formatFiletypes = {
      sh = 'shfmt',
    },
    formatters = {
      shfmt = shfmt,
    },
    linters = {
      shellcheck = shellcheck,
    },
  },
}

EOF

