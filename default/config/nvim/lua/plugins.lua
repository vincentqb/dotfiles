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

  -- Keymap discoverability
  {
    'folke/which-key.nvim',
    event = 'VeryLazy',
    opts = {},
  },

  -- Prettier diagnostic/quickfix list
  {
    'folke/trouble.nvim',
    cmd = 'Trouble',
    keys = {
      { '<Leader>xx', '<cmd>Trouble diagnostics toggle<cr>',              desc = 'Diagnostics (Trouble)' },
      { '<Leader>xX', '<cmd>Trouble diagnostics toggle filter.buf=0<cr>', desc = 'Buffer Diagnostics (Trouble)' },
      { '<Leader>xl', '<cmd>Trouble loclist toggle<cr>',                  desc = 'Location List (Trouble)' },
      { '<Leader>xq', '<cmd>Trouble qflist toggle<cr>',                   desc = 'Quickfix List (Trouble)' },
    },
    opts = {},
  },

  -- Spell dictionary is now self-maintained at spell/programming.utf-8.add
  -- (collated from vim-dirtytalk master + open PR #45; plugin removed)

  -- Treesitter (main branch; master is unmaintained and broken on nvim 0.12).
  -- The rewrite drops the `configs` module: parsers install via :TSInstall or
  -- the install_dir setup, and highlighting is started per-buffer by us.
  {
    'nvim-treesitter/nvim-treesitter',
    branch = 'main',
    build = ':TSUpdate',
    lazy = false,
  },
  {
    'nvim-treesitter/nvim-treesitter-textobjects',
    branch = 'main',
    dependencies = { 'nvim-treesitter/nvim-treesitter' },
    event = { 'BufReadPost', 'BufNewFile' },
  },

  -- AI tooling
  'awslabs/amazonq.nvim',
  'olimorris/codecompanion.nvim',
}
