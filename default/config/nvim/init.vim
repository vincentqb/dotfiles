set runtimepath^=~/.vim runtimepath+=~/.vim/after
let &packpath = &runtimepath
source ~/.vimrc

" Specify python to use in nvim
" Python 3
let g:python3_host_prog='/usr/bin/python3'
" Python 2
let g:python_host_prog='/usr/bin/python'

lua << EOF

-- Languange Server Protocol

require'lspconfig'.pylsp.setup{
    settings = {
        pylsp = {
            plugins = {
                flake8 = {
                    maxLineLength = 100,
                }
            }
        }
    }
}

require'lspconfig'.bashls.setup{}
require'lspconfig'.texlab.setup{}

EOF

autocmd Filetype python setlocal omnifunc=v:lua.vim.lsp.omnifunc
