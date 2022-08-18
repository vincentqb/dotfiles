-- Activate spellchecker
vim.opt.spell = true
vim.opt.spelllang = { 'en_us' }

-- Specify Python 3 to use
vim.g.python3_host_prog = '/usr/bin/python3'
-- Specify Python 2 to use
vim.g.python_host_prog = '/usr/bin/python'

-- Fold using indentation
vim.cmd([[
	au FileType python set foldmethod=indent foldnestmax=1 foldminlines=10
	au FileType python nnoremap <space> za
]])

-- Automatic indentation
vim.opt.smartindent = true
vim.opt.breakindent = true
vim.opt.breakindentopt = "shift:2,min:40,sbr"
vim.opt.showbreak = ">>"

-- Persistent undo tree, but careful about leaking sensitive information
vim.opt.undofile = true

-- Search and highlight while typing while ignoring case when only lower case used
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.incsearch = true
vim.opt.hlsearch = true

-- Use spaces for tabs
vim.opt.tabstop = 4
vim.opt.softtabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = 4

-- Show matching brackets.
vim.opt.showmatch = true

-- Automatically save before commands like :next and :make
vim.opt.autowrite = true

-- https://dev.to/vonheikemen/creating-a-lua-interface-for-minpac-1jd2
function PackInit()
  vim.cmd('packadd minpac')

  vim.call('minpac#init')
  local add = vim.fn['minpac#add']

  -- Additional plugins here.
  add('k-takata/minpac', {type = 'opt'})
  add('vim-jp/syntax-vim-ex')
  add('tyru/open-browser.vim')
end

-- Define user commands for updating/cleaning the plugins.
-- Each of them calls PackInit() to load minpac and register
-- the information of plugins, then performs the task.
vim.cmd [[
  command! PackUpdate lua PackInit(); vim.call('minpac#update')
  command! PackClean  lua PackInit(); vim.call('minpac#clean')
  command! PackStatus lua PackInit(); vim.call('minpac#status')
]]
