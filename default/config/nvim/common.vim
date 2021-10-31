" F5 to show undo tree
nnoremap <F5> :UndotreeToggle<CR>

" Peristent undo tree
if has("persistent_undo")
    if has('vim')
        set undodir=$HOME."/.config/nvim/undodir"
    endif
    if has('nvim')
        set undodir=$HOME/.config/nvim/undodir
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
" set mouse=a		" Enable mouse usage (all modes)
