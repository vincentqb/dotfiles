-- Plugin specifications for lazy.nvim
-- Managed via ~/.local/share/nvim/lazy/; lockfile committed as lazy-lock.json
return {
  -- Colorscheme
  {
    'dracula/vim',
    name = 'dracula',
    lazy = false,
    priority = 1000,
    init = function()
      vim.g.dracula_colorterm = 0
    end,
    config = function()
      vim.cmd.colorscheme('dracula')
    end,
  },

  -- Editing
  'thinca/vim-visualstar',
  'AndrewRadev/linediff.vim',
  'tpope/vim-surround',
  'chrisbra/Recover.vim',
  { 'mbbill/undotree', cmd = 'UndotreeToggle' },

  -- Database
  'tpope/vim-dadbod',

  -- Git
  {
    'lewis6991/gitsigns.nvim',
    event = { 'BufReadPre', 'BufNewFile' },
    opts = {},
  },

  -- Dependencies
  'nvim-lua/plenary.nvim',

  -- Telescope
  {
    'nvim-telescope/telescope.nvim',
    tag = '0.1.8',
    dependencies = { 'nvim-lua/plenary.nvim' },
    cmd = 'Telescope',
    keys = {
      { '<Leader>ff', '<cmd>Telescope find_files<cr>' },
      { '<Leader>fg', '<cmd>Telescope live_grep<cr>' },
      { '<Leader>fb', '<cmd>Telescope buffers<cr>' },
      { '<Leader>fh', '<cmd>Telescope help_tags<cr>' },
    },
  },

  -- LSP
  {
    'neovim/nvim-lspconfig',
    event = { 'BufReadPre', 'BufNewFile' },
  },

  -- Completion (replaces the entire nvim-cmp stack)
  {
    'saghen/blink.cmp',
    version = '*',
    event = { 'InsertEnter', 'CmdlineEnter' },
    opts = {
      keymap = { preset = 'default' },
      completion = {
        documentation = { auto_show = true },
      },
      sources = {
        default = { 'lsp', 'path', 'snippets', 'buffer' },
      },
    },
  },

  -- Statusline
  {
    'nvim-lualine/lualine.nvim',
    event = 'VeryLazy',
  },

  -- Spell dictionary
  'psliwka/vim-dirtytalk',

  -- Treesitter (pin to master; main branch removed the `configs` module API)
  {
    'nvim-treesitter/nvim-treesitter',
    branch = 'master',
    build = ':TSUpdate',
    event = { 'BufReadPost', 'BufNewFile' },
  },

  -- AI tooling
  'awslabs/amazonq.nvim',
  'olimorris/codecompanion.nvim',
}
