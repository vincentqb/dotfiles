set runtimepath^=~/.vim runtimepath+=~/.vim/after
let &packpath = &runtimepath
" source ~/.vimrc

runtime! plugin/sensible.vim

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

let g:LanguageClient_serverCommands = {
    \ 'python': ['pyls', '-vv', '--log-file', '~/pyls.log'],
    \ }

packadd! dracula
syntax enable
colorscheme dracula

" F5 to show undo tree
nnoremap <F5> :UndotreeToggle<CR>

" Peristent undo tree
if has("persistent_undo")
    if has('vim')
        set undodir=$HOME."/.undodir"
    endif
    if has('nvim')
        set undodir=$HOME/.undodir
    endif
    set undofile
endif

set smartindent
set breakindent
set breakindentopt=shift:2,min:40,sbr
set showbreak=>>
" Fold using indentation
au FileType python set foldmethod=indent
au FileType python set foldnestmax=1
au FileType python set foldminlines=10
" Open/close folds with space
au FileType python nnoremap <space> za

" Search and highlight while typing while ignoring case when only lower case used
set ignorecase
set smartcase
set incsearch
set hlsearch

" Use spaces for tabs
set tabstop=4
set softtabstop=4
set shiftwidth=4
set expandtab

" The following are commented out as they cause vim to behave a lot
" differently from regular Vi. They are highly recommended though.
set showcmd		" Show (partial) command in status line.
set showmatch		" Show matching brackets.
set autowrite		" Automatically save before commands like :next and :make
set hidden		" Hide buffers when they are abandoned
set mouse=a		" Enable mouse usage (all modes)
