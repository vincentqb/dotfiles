require('codecompanion').setup({
  display = {
    chat = {
      window = {
        width = 0.33,
      },
    },
  },
  interactions = {
    chat = {
      adapter = "kiro",
      model = "claude-opus-4.6-1m",
    },
    inline = {
      adapter = "anthropic",
      model = "claude-opus-4-6",
    },
    cli = {
      agent = "kiro",
      agents = {
        kiro = {
          cmd = "kiro-cli",
          args = { "chat" },
          description = "Kiro (Claude Opus 4.6 1M)",
          provider = "terminal",
        },
      },
    },
  },
})
