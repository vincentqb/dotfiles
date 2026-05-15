-- nvim-treesitter `main` branch.
--
-- The rewrite removed `require('nvim-treesitter.configs').setup({...})` —
-- there is no central setup API. Instead:
--   * Parsers install via :TSInstall <lang>, :TSUpdate, or this script's
--     ensure_installed list at startup.
--   * Highlighting is started per-buffer with vim.treesitter.start(); we
--     wire that up in a FileType autocmd.
--   * Indentation, incremental selection, and textobjects all moved to
--     separate plugins. We use nvim-treesitter-textobjects below.

local ensure_installed = {
  'c', 'lua', 'vim', 'vimdoc', 'query', 'markdown', 'markdown_inline', 'python',
}

-- Install missing parsers in the background. main exposes nvim_treesitter.install.
local ts = require('nvim-treesitter')
if ts.install then
  ts.install(ensure_installed):wait(60000)
end

-- Auto-start treesitter on filetypes whose parsers are installed.
vim.api.nvim_create_autocmd('FileType', {
  callback = function(args)
    local ft = vim.bo[args.buf].filetype
    local lang = vim.treesitter.language.get_lang(ft)
    if not lang then return end
    -- Only start if a parser is actually installed; otherwise nvim throws.
    local ok = pcall(vim.treesitter.start, args.buf, lang)
    if ok then
      vim.bo[args.buf].syntax = ''       -- disable regex syntax (treesitter wins)
      vim.wo.foldmethod = 'expr'
      vim.wo.foldexpr = 'v:lua.vim.treesitter.foldexpr()'
    end
  end,
})

-- Textobjects via nvim-treesitter-textobjects (separate plugin in main).
-- Select/move/swap by syntactic node (function, class, parameter, etc.).
local select_keymaps = {
  ['af'] = '@function.outer',
  ['if'] = '@function.inner',
  ['ac'] = '@class.outer',
  ['ic'] = '@class.inner',
  ['aa'] = '@parameter.outer',
  ['ia'] = '@parameter.inner',
}
for lhs, capture in pairs(select_keymaps) do
  vim.keymap.set({ 'x', 'o' }, lhs, function()
    require('nvim-treesitter-textobjects.select').select_textobject(capture, 'textobjects')
  end)
end

local move_next = { [']f'] = '@function.outer', [']c'] = '@class.outer' }
local move_prev = { ['[f'] = '@function.outer', ['[c'] = '@class.outer' }
for lhs, capture in pairs(move_next) do
  vim.keymap.set({ 'n', 'x', 'o' }, lhs, function()
    require('nvim-treesitter-textobjects.move').goto_next_start(capture, 'textobjects')
  end)
end
for lhs, capture in pairs(move_prev) do
  vim.keymap.set({ 'n', 'x', 'o' }, lhs, function()
    require('nvim-treesitter-textobjects.move').goto_previous_start(capture, 'textobjects')
  end)
end

-- Incremental selection: main dropped it. Use built-in `vit`/`vat` plus
-- text-objects above instead. (Kept as a note rather than re-implementing.)
