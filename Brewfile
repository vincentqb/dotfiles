# `brew bundle` hands subprocesses a stripped PATH — Homebrew's shims plus
# /usr/bin — where the only python is the system's 3.7. uv then falls back to a
# managed interpreter, which reports the *system* glibc (2.26 on Amazon Linux),
# below the manylinux_2_28 floor that numpy >=2.3 ships to; uv rejects the wheels
# and compiles against gcc 7.3.1, which fails. Put brew's bin back on PATH so the
# python-preference = "system" in config/uv/uv.toml can find brew's python, which
# reports brew's own glibc.
ENV["PATH"] = "#{ENV.fetch("HOMEBREW_PREFIX", "/home/linuxbrew/.linuxbrew")}/bin:#{ENV["PATH"]}"

# Shell / terminal
brew "coreutils"
brew "fish"
brew "tmux"
brew "ansifilter"   # tmux-logging
cask "kitty"

# CLI core
brew "bat"
brew "eza"
brew "fd"
brew "fzf"
brew "just"
brew "ripgrep"
brew "rsync"
brew "wget"
brew "autossh"

# Git
brew "gh"

# Editors / nvim provider
brew "neovim"
brew "tree-sitter-cli"  # parser compiler for nvim-treesitter (main branch)

# Languages / toolchains
brew "node"
brew "rustup"
brew "uv"
brew "elan-init"
brew "glibc"

# Python tooling
brew "python@3.14"  # uv's default interpreter, via python-preference = "system"
brew "ruff"

# AI tooling
tap "anomalyco/tap"             # OpenCode (custom tap, always up to date)
brew "anomalyco/tap/opencode"
# cask "claude-code"
# cask "kiro-cli"
brew "bubblewrap"
# cask "codex"
brew "ollama"
brew "ccusage"
uv "cli-agent-orchestrator", source: "git+https://github.com/awslabs/cli-agent-orchestrator.git@main"
brew "slirp4netns"

# Docs / writing
brew "biber"        # biblatex bibliographies
brew "pandoc"
brew "texlive"

# Shell scripting
brew "shellcheck"

# Cloud
brew "awscli"

# Cargo
cargo "cargo-update"

# uv tools
uv "dot-py"
uv "pre-commit"
uv "pynvim"

# Optional — uncomment as needed
# brew "colima"
# brew "docker", link: false
# brew "docker-compose"
# brew "imagemagick"
# brew "maven"
# brew "python-tk@3.14"
# brew "yarn"
# cask "amazon-q"
# cask "docker-desktop"
# cask "tabby"
# cask "wezterm@nightly"
# cargo "generate-bidi"
# cargo "strip-ansi-escapes"
# cargo "sync-color-schemes"
# cargo "wezterm"
