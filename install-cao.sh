#!/bin/bash

# cli-agent-orchestrator (CAO), against brew-provided deps.
# Amazon Linux's system libs are too old; brew gives us tmux >=3.3 and uv,
# and uv fetches its own standalone Python >=3.10 — so CAO links nothing
# against the host's ancient libraries.
set -euo pipefail

eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
brew install tmux uv python@3.13

# Build with brew's Python, not uv's bundled one: uv's standalone Python
# detects the *system* glibc (2.26), below numpy's manylinux_2_28 floor, so uv
# rejects every wheel and compiles against gcc 7.3.1 (fails). Brew's Python
# reports glibc 2.39, so uv installs prebuilt wheels — nothing compiles.
uv tool install --upgrade \
  --python /home/linuxbrew/.linuxbrew/bin/python3.13 \
  git+https://github.com/awslabs/cli-agent-orchestrator.git@main

cao --help
