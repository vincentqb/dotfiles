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

" Show line numbers
set relativenumber
set number

" Combined status and command bars but hides vim-mode unless using something like lualine
" set cmdheight=0

" Show matching brackets.
set showmatch

" Fuzzy cli completion
set wildoptions+=fuzzy

" Add vertical line to highlight column were row is too long
set colorcolumn=120

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

" https://vi.stackexchange.com/questions/454/whats-the-simplest-way-to-strip-trailing-whitespace-from-all-lines-in-a-file
fun! TrimWhitespace()
    let l:save = winsaveview()
    keeppatterns %s/\s\+$//e
    call winrestview(l:save)
endfun
noremap <F6> <cmd>call TrimWhitespace()<CR>

function! PackInit() abort
    packadd minpac

    call minpac#init()
    call minpac#add('k-takata/minpac', {'type': 'opt'})
    call minpac#add('dracula/vim', {'name': 'dracula'})

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

    " call minpac#add('lervag/vimtex')

    call minpac#add('neovim/nvim-lspconfig')

    " Autocompletion plugin
    " https://github.com/neovim/nvim-lspconfig/issues/130#issuecomment-992678432
    " Plug 'maralla/completor.vim'  " enables code completion - https://github.com/maralla/completor.vim
    " Plug 'prabirshrestha/asyncomplete.vim'  " code completion with support for LSP
    " Plug 'ervandew/supertab'  " enables tab actions i.e. autocomplete by using <tab> insert mode
    " Plug 'lifepillar/vim-mucomplete'  " enables code completion (popup)

    " Autocompletion plugin
    " https://github.com/hrsh7th/nvim-cmp/
    call minpac#add('hrsh7th/nvim-cmp')
    call minpac#add('hrsh7th/cmp-nvim-lsp')
    call minpac#add('hrsh7th/cmp-buffer')
    call minpac#add('hrsh7th/cmp-path')
    call minpac#add('hrsh7th/cmp-cmdline')
    call minpac#add('hrsh7th/cmp-vsnip')
    call minpac#add('hrsh7th/vim-vsnip')
    " https://github.com/neovim/nvim-lspconfig/wiki/Autocompletion
    " call minpac#add('saadparwaiz1/cmp_luasnip') " Snippets source for nvim-cmp
    " call minpac#add('L3MON4D3/LuaSnip') " Snippets plugin

    call minpac#add('nvim-lualine/lualine.nvim')
    " call minpac#add('nvim-tree/nvim-web-devicons')

    call minpac#add('vincentqb/vimwhisperer')

    " Run :DirtytalkUpdate manually
    " https://github.com/psliwka/vim-dirtytalk/issues/1
    " call minpac#add('psliwka/vim-dirtytalk', {'do': 'DirtytalkUpdate'})
    call minpac#add('psliwka/vim-dirtytalk')

endfunction

command! PackUpdate call PackInit() | call minpac#update()
command! PackClean  call PackInit() | call minpac#clean()
command! PackStatus packadd minpac | call minpac#status()

" Code completion with Amazon Q
map <F12> :silent! call CodeWhisperer()<CR>

" Enable theme
" https://github.com/dracula/vim/issues/96
" let g:dracula_italic = 0
let g:dracula_colorterm = 0
colorscheme dracula

" Toggle show undo tree
nnoremap <F2> <cmd>UndotreeToggle<CR>

" Set vimtex
let g:tex_flavor = 'latex'
let g:vimtex_compiler_progname = 'nvr'
" https://github.com/lervag/vimtex/issues/1430
let g:vimtex_indent_on_ampersands = 0

" import lua/init.lua
lua require("init")
