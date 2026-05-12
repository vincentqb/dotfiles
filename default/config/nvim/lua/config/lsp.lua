-- Language Server Protocol
-- https://github.com/neovim/nvim-lspconfig
-- vim.lsp.set_log_level("debug")

-- Buffer-local keymaps set when an LSP attaches
local on_attach = function(_, bufnr)
  vim.bo[bufnr].omnifunc = 'v:lua.vim.lsp.omnifunc'

  local bufopts = { noremap = true, silent = true, buffer = bufnr }

  vim.keymap.set('n', '[d', function()
    vim.diagnostic.jump({ count = -1, float = true })
  end, bufopts)
  vim.keymap.set('n', ']d', function()
    vim.diagnostic.jump({ count = 1, float = true })
  end, bufopts)

  vim.keymap.set('n', '<F5>', vim.diagnostic.open_float, bufopts)

  vim.keymap.set('n', 'gd', vim.lsp.buf.definition, bufopts)
  vim.keymap.set('n', 'K', vim.lsp.buf.hover, bufopts)
  vim.keymap.set('n', 'gr', vim.lsp.buf.references, bufopts)

  -- Format then organize imports (Ruff)
  vim.keymap.set('n', '<F4>', function()
    vim.lsp.buf.format({ async = false })
    vim.lsp.buf.code_action({
      context = {
        only = { 'source.organizeImports' },
        diagnostics = {},
      },
      apply = true,
    })
  end, bufopts)
end

-- Completion capabilities from blink.cmp
local capabilities = require('blink.cmp').get_lsp_capabilities()

local servers = { 'texlab', 'ruff', 'ty' }
for _, lsp in ipairs(servers) do
  vim.lsp.config(lsp, {
    on_attach = on_attach,
    capabilities = capabilities,
  })
  vim.lsp.enable(lsp)
end
