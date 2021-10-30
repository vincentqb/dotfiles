set runtimepath^=~/.vim runtimepath+=~/.vim/after
let &packpath = &runtimepath
source ~/.vimrc

" Specify python to use in nvim
" Python 3
let g:python3_host_prog='/usr/bin/python3'
" Python 2
let g:python_host_prog='/usr/bin/python'

" Languange Server Protocol
lua  << EOF
    require'lspconfig'.pylsp.setup{}
    require'lspconfig'.bashls.setup{}
EOF
autocmd Filetype python setlocal omnifunc=v:lua.vim.lsp.omnifunc

" let g:LanguageClient_serverCommands = {
"     \ 'python': ['pyls', '-vv', '--log-file', '~/pyls.log'],
"     \ }
