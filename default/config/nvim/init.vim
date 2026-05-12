" Set <Leader> to be something else than default \\ below
" let g:mapleader="\\"

" Specify Python 3 to use (pynvim installed via `uv tool install pynvim`)
let g:python3_host_prog = expand('~/.local/bin/pynvim-python')
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

" Enable '+' system clipboard with +yy
set clipboard+=unnamedplus

" Persistent undo tree, but careful about leaking sensitive information
set undofile

" Search and highlight while typing while ignoring case when only lower case used
set ignorecase
set smartcase

" Show line numbers
set relativenumber
set number

" Hides command line unless used
" set cmdheight=0
" Disable showing mode in command line, relevant when using lualine, clear with Ctrl-L redraw
" set noshowmode

" Show matching brackets.
set showmatch

" Fuzzy cli completion
set wildoptions+=fuzzy

" Add vertical line to highlight column were row is too long
set colorcolumn=120
set synmaxcol=1200

" Add horizontal line
" set cursorline
" highlight CursorLine ctermbg=lightgrey guibg=lightgrey
" highlight CursorLine ctermbg=black guibg=black

" Automatically save before commands like :next and :make
set autowrite

" Activate spellchecker
set spelllang=en_us,programming
set spellsuggest+=10
" Spell-check Markdown files and Git Commit Messages
au FileType markdown set spell
au FileType tex set spell
au FileType gitcommit set spell
" autocmd FileType markdown setlocal spell
" Disable spellcheck in python by default
" autocmd FileType python setlocal nospell
" Toggle spellchecking
noremap <F3> :setlocal spell! spelllang=en_us,programming<CR>

" https://vim.fandom.com/wiki/Omni_completion
set omnifunc=syntaxcomplete#Complete
" imap <c-n> <c-x><c-o>
" imap <c-n> <c-o><c-n>
set pumheight=7

" Plugins are managed by lazy.nvim (see lua/plugins.lua).
" Telescope keymaps, dracula colorscheme, and plugin setup are declared there.

" Code completion with Amazon Q
" map <F12> :silent! call CodeWhisperer()<CR>

" Toggle show undo tree
nnoremap <F2> <cmd>UndotreeToggle<CR>

" Set vimtex
let g:tex_flavor = 'latex'
let g:vimtex_compiler_progname = 'nvr'
" https://github.com/lervag/vimtex/issues/1430
let g:vimtex_indent_on_ampersands = 0

" Disable line numbers in terminal and codecompanion buffers
au FileType codecompanion setlocal nonumber norelativenumber

" import lua/init.lua
lua require("init")
