" Load default Vim8 configuration
source $VIMRUNTIME/defaults.vim

call plug#begin('~/.vim/plugged')
	Plug 'tpope/vim-sensible'
	Plug 'thinca/vim-visualstar'
	Plug 'tmhedberg/SimpylFold'
	Plug 'endel/vim-github-colorscheme'
	Plug 'ervandew/supertab'
	Plug 'AndrewRadev/linediff.vim'

	Plug 'w0rp/ale'
	" Plug 'desmap/ale-sensible'
	" Plug 'Valloric/YouCompleteMe'
	" Plug 'Valloric/YouCompleteMe', { 'do': './install.py' }
	"
	Plug 'shougo/deoplete.nvim'
	Plug 'roxma/nvim-yarp'
	Plug 'roxma/vim-hug-neovim-rpc'  " pip3 install neovim
	" Plug 'deoplete-plugins/deoplete-jedi'  " Python autocomplete

	Plug 'vimjas/vim-python-pep8-indent'
call plug#end()

colorscheme github

let g:deoplete#enable_at_startup = 1
let b:ale_linters = ['flake8', 'pylint']
let b:ale_fixers = ['autopep8', 'yapf']
let g:ale_lint_on_text_changed = 'never'
let g:ale_set_highlights = 0

set smartindent

" Fold using indentation
au FileType python set foldmethod=indent
au FileType python set foldnestmax=1
" au FileType python set foldminlines=20
" Open/close folds with space
au FileType python nnoremap <space> za

""""" Search while typing while ignoring case (when only lower case used)
set ignorecase
set smartcase
set incsearch

""""" Press escape to clear previous search highlight
" nnoremap <esc> :noh<return><esc>

" Automatically turn on/off paste mode when pasting to avoid stacking indentation

let &t_SI .= "\<Esc>[?2004h"
let &t_EI .= "\<Esc>[?2004l"

let &t_SI .= "\<Esc>[?2004h"
let &t_EI .= "\<Esc>[?2004l"

inoremap <special> <expr> <Esc>[200~ XTermPasteBegin()

function! XTermPasteBegin()
        set pastetoggle=<Esc>[201~
        set paste
        return ""
endfunction
