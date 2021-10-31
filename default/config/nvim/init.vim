set runtimepath^=~/.vim runtimepath+=~/.vim/after
let &packpath = &runtimepath
source ~/.vimrc

" Specify python to use in nvim
" Python 3
let g:python3_host_prog='/usr/bin/python3'
" Python 2
let g:python_host_prog='/usr/bin/python'

" Languange Server Protocol
lua << EOF


local lspconfig = require 'lspconfig'
local on_attach = function(_, bufnr)

  local function buf_set_keymap(...) vim.api.nvim_buf_set_keymap(bufnr, ...) end
  local function buf_set_option(...) vim.api.nvim_buf_set_option(bufnr, ...) end

  -- Enable completion triggered by <c-x><c-o>
  buf_set_option('omnifunc', 'v:lua.vim.lsp.omnifunc')

end

lspconfig.pylsp.setup{
    settings = {
        pylsp = {
            plugins = {
                flake8 = {
                    maxLineLength = 100
                }
            }
        }
    }
}

lspconfig.bashls.setup{}
lspconfig.texlab.setup{}

local shfmt = require 'lsp.diagnosticls.formatters.shfmt'
local shellcheck = require 'lsp.diagnosticls.linters.shellcheck'

lspconfig.diagnosticls.setup {
  on_attach = on_attach,
  filetypes = { 'sh', 'yaml', 'lua' },
  init_options = {
    filetypes = {
      sh = 'shellcheck',
      yaml = 'yamllint',
    },
    formatFiletypes = {
      sh = 'shfmt',
    },
    formatters = {
      shfmt = shfmt,
    },
    linters = {
      shellcheck = shellcheck,
    },
  },
}

EOF

