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

" Fuzzy cli completion
set wildoptions+=fuzzy

" Add vertical line to highlight column were row is too long
set colorcolumn=120

" Automatically save before commands like :next and :make
set autowrite

" Activate spellchecker
set spelllang=en_us,programming
" Spell-check Markdown files and Git Commit Messages
au FileType markdown set spell
au FileType tex set spell
au FileType gitcommit set spell
" autocmd FileType markdown setlocal spell
" Disable spellcheck in python by default
" autocmd FileType python setlocal nospell
" Toggle spellchecking
map <F3> :setlocal spell! spelllang=en_us,programming<CR>

function! PackInit() abort
    packadd minpac

    call minpac#init()
    call minpac#add('k-takata/minpac', {'type': 'opt'})
    call minpac#add('dracula/vim', { 'name': 'dracula' })
    " call minpac#add('folke/tokyonight.nvim')

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

    " call minpac#add('psf/black')
    call minpac#add('neovim/nvim-lspconfig')
    " call minpac#add('lervag/vimtex')
    " call minpac#add('hrsh7th/nvim-cmp')
    " call minpac#add('hrsh7th/cmp-vsnip')
    " call minpac#add('hrsh7th/vim-vsnip')

    call minpac#add('hrsh7th/nvim-cmp') " Autocompletion plugin
    call minpac#add('hrsh7th/cmp-nvim-lsp') " LSP source for nvim-cmp

    " https://github.com/hrsh7th/nvim-cmp/
    call minpac#add('hrsh7th/cmp-buffer')
    call minpac#add('hrsh7th/cmp-path')
    call minpac#add('hrsh7th/cmp-cmdline')
    call minpac#add('hrsh7th/nvim-cmp')
    " call minpac#add('hrsh7th/cmp-vsnip')
    " call minpac#add('hrsh7th/vim-vsnip')

    " https://github.com/neovim/nvim-lspconfig/wiki/Autocompletion
    call minpac#add('saadparwaiz1/cmp_luasnip') " Snippets source for nvim-cmp
    call minpac#add('L3MON4D3/LuaSnip') " Snippets plugin

    " call minpac#add('vimwiki/vimwiki')
    " Run :DirtytalkUpdate manually
    " https://github.com/psliwka/vim-dirtytalk/issues/1
    " call minpac#add('psliwka/vim-dirtytalk', {'do': ':let &rtp = &rtp \| DirtytalkUpdate' })
    call minpac#add('psliwka/vim-dirtytalk', {'do': ':DirtytalkUpdate'})

endfunction

command! PackUpdate call PackInit() | call minpac#update()
command! PackClean  call PackInit() | call minpac#clean()
command! PackStatus packadd minpac | call minpac#status()

" https://sw.kovidgoyal.net/kitty/faq/#i-get-errors-about-the-terminal-being-unknown-or-opening-the-terminal-failing-when-sshing-into-a-different-computer
" Mouse support
" set mouse=a
" set ttymouse=sgr
" set balloonevalterm
" Styled and colored underline support
let &t_AU = "\e[58:5:%dm"
let &t_8u = "\e[58:2:%lu:%lu:%lum"
let &t_Us = "\e[4:2m"
let &t_Cs = "\e[4:3m"
let &t_ds = "\e[4:4m"
let &t_Ds = "\e[4:5m"
let &t_Ce = "\e[4:0m"
" Strikethrough
let &t_Ts = "\e[9m"
let &t_Te = "\e[29m"
" Truecolor support
let &t_8f = "\e[38:2:%lu:%lu:%lum"
let &t_8b = "\e[48:2:%lu:%lu:%lum"
let &t_RF = "\e]10;?\e\\"
let &t_RB = "\e]11;?\e\\"
" Bracketed paste
let &t_BE = "\e[?2004h"
let &t_BD = "\e[?2004l"
let &t_PS = "\e[200~"
let &t_PE = "\e[201~"
" Cursor control
let &t_RC = "\e[?12$p"
let &t_SH = "\e[%d q"
let &t_RS = "\eP$q q\e\\"
let &t_SI = "\e[5 q"
let &t_SR = "\e[3 q"
let &t_EI = "\e[1 q"
let &t_VS = "\e[?12l"
" Focus tracking
let &t_fe = "\e[?1004h"
let &t_fd = "\e[?1004l"
" execute "set <FocusGained>=\<Esc>[I"
" execute "set <FocusLost>=\<Esc>[O"
" Window title
let &t_ST = "\e[22;2t"
let &t_RT = "\e[23;2t"

" vim hardcodes background color erase even if the terminfo file does
" not contain bce. This causes incorrect background rendering when
" using a color theme with a background color in terminals such as
" kitty that do not support background color erase.
let &t_ut=''

" Enable theme
" https://github.com/dracula/vim/issues/96
" let g:dracula_italic = 0
let g:dracula_colorterm = 0
colorscheme dracula
" colorscheme tokyonight-night
" colorscheme tokyonight-storm
" colorscheme tokyonight-moon

" Add horizontal line
" set cursorline
" highlight CursorLine ctermbg=lightgrey guibg=lightgrey
" highlight CursorLine ctermbg=black guibg=black

" Toggle show undo tree
nnoremap <F2> <cmd>UndotreeToggle<CR>

" Set default directory for vimwiki files
" let g:vimwiki_list = [{'path': "~/wiki"}]
" hi def VimwikiDelText term=strikethrough cterm=strikethrough gui=strikethrough
" hi VimwikiDelText term=strikethrough cterm=strikethrough gui=strikethrough
" Set vimwiki colors for each heading level: default is all same color
" hi VimwikiHeader1 ctermfg=Green
" hi VimwikiHeader2 ctermfg=Cyan
" hi VimwikiHeader3 ctermfg=Blue
" hi VimwikiHeader4 ctermfg=Yellow
" hi VimwikiHeader5 ctermfg=Red
" hi VimwikiHeader6 ctermfg=Brown

" Set vimtex
let g:tex_flavor = 'latex'
let g:vimtex_compiler_progname = 'nvr'
" https://github.com/lervag/vimtex/issues/1430
let g:vimtex_indent_on_ampersands = 0

" https://vim.fandom.com/wiki/Omni_completion
set omnifunc=syntaxcomplete#Complete
" imap <c-n> <c-x><c-o>
" imap <c-n> <c-o><c-n>

" Make LSP messages appear above the current line
" https://github.com/neovim/nvim-lspconfig/issues/1046
" map <leader>d <cmd>lua vim.diagnostic.open_float(0, {scope="line"})<CR>
map <F5> <cmd>lua vim.diagnostic.open_float(0, {scope="line"})<CR>

" https://vi.stackexchange.com/questions/454/whats-the-simplest-way-to-strip-trailing-whitespace-from-all-lines-in-a-file
fun! TrimWhitespace()
    let l:save = winsaveview()
    keeppatterns %s/\s\+$//e
    call winrestview(l:save)
endfun
noremap <F6> <cmd>call TrimWhitespace()<CR>
noremap <F4> <cmd>lua vim.lsp.buf.format()<CR>

lua require("init")
