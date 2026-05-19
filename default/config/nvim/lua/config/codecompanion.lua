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
      model = "claude-opus-4.7-1m",
    },
    inline = {
      adapter = "anthropic",
      model = "claude-opus-4-7",
    },
    cli = {
      agent = "kiro",
      agents = {
        kiro = {
          cmd = "kiro-cli",
          args = { "chat" },
          description = "Kiro (Claude Opus 4.7 1M)",
          provider = "terminal",
        },
      },
    },
  },
})
