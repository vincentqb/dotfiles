#!/bin/bash

git submodule sync
git submodule update --init --recursive

# Homebrew + everything in the Brewfile (formulae, cargo, uv tools)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
brew update
brew bundle

# Neovim plugins via lazy.nvim
nvim --headless "+Lazy! sync" +qa

# Cargo + zenith (not packaged in brew with nvidia feature)
curl https://sh.rustup.rs -sSf | sh -s -- -y
~/.cargo/bin/cargo install --features nvidia --git https://github.com/bvaisvil/zenith.git
~/.cargo/bin/cargo install-update -a

toolbox install codex
toolbox install claude-code --channel head

# Start assistant with /claudeclaw:start
claude plugin marketplace add moazbuilds/claudeclaw
claude plugin install claudeclaw

toolbox install kiro-cli --force
toolbox install aim
aim mcp install quicksight-mcp
claude mcp add --scope user quicksight-mcp /local/home/quennv/.aim/mcp-servers/quicksight-mcp

toolbox install AndesCli
aim mcp install andes-mcp

toolbox install arcc-cli
aim mcp install arcc-mcp

aim agents install ChorusAIM

aim skills install AmazonSharePointMCP
aim mcp install amazon-sharepoint-mcp
aim install amazon-sharepoint-mcp

aim agents install InventoryTransferServiceAgentAIM
aim plugins install InventoryTransferServiceAgentAIM

aim agents install StoreGenAICapabilities
aim skills install StoreGenAICapabilities
aim plugins install StoreGenAICapabilities-1.0

aim agents install IRRGenAICapabilities
aim skills install IRRGenAICapabilities

aim agents install OptimusPrimeKiro
aim skills install OptimusPrimeKiro

aim mcp install software-builder-insights-prod-mcp

# toolbox registry add s3://buildertoolbox-registry-grasp-tools-us-west-2/tools.json
# toolbox install grasp-mcp
# grasp-mcp config initialize
# grasp-mcp login

aim agents update
aim mcp update
aim skills update

# CAO
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
brew install tmux uv python@3.13
uv tool install --upgrade \
  --python /home/linuxbrew/.linuxbrew/bin/python3.13 \
  git+https://github.com/awslabs/cli-agent-orchestrator.git@main
cao install code_supervisor
