" Activate spellchecker
set spell spelllang=en_us

" Enable syntax highlighting
syntax enable

" Automatic indentation
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

" Show matching brackets.
set showmatch

" Automatically save before commands like :next and :make
set autowrite
