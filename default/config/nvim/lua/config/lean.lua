-- lean.nvim starts the project's Lean server and displays goals/hypotheses.
-- Configure it before its plugin and filetype scripts run.
vim.g.lean_config = {
  mappings = true,
}

local function set_highlights()
  -- Lean marks sorry/admit with a custom semantic token type.
  vim.api.nvim_set_hl(0, '@lsp.type.leanSorryLike.lean', {
    link = 'Error',
    default = true,
  })
end

vim.api.nvim_create_autocmd('ColorScheme', {
  group = vim.api.nvim_create_augroup('LeanHighlights', { clear = true }),
  callback = set_highlights,
})
set_highlights()
