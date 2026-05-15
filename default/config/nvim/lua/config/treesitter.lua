-- nvim-treesitter `main` branch.
--
-- The rewrite removed the central setup({...}) API. We just install parsers
-- and start treesitter per-buffer. Folding is opt-in per-filetype (see
-- init.vim's FileType python autocmd).

local ensure_installed = {
  'c', 'lua', 'vim', 'vimdoc', 'query', 'markdown', 'markdown_inline', 'python',
}

local ts = require('nvim-treesitter')
if ts.install then
  ts.install(ensure_installed):wait(60000)
end

-- Auto-start treesitter on filetypes whose parsers are installed.
vim.api.nvim_create_autocmd('FileType', {
  callback = function(args)
    local lang = vim.treesitter.language.get_lang(vim.bo[args.buf].filetype)
    if not lang then return end
    if pcall(vim.treesitter.start, args.buf, lang) then
      vim.bo[args.buf].syntax = ''
    end
  end,
})
