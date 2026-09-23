#!/bin/bash
# One row of `astra-probe`: does GPT-6 Astra answer through the *regular Bedrock
# Runtime* endpoint instead of Mantle?
#
# BuilderHub's documented escape hatch for regional availability is the
# Amazon-specific `bedrock_provider` switch, which lives OUTSIDE ~/.codex (see
# `codex amzn directories`) and has no `-c` / env override -- the only way to
# test it is to edit that file. So the flip happens here, under a trap that
# restores the original on any exit, rather than in the fish caller.
#
# Prints one word: OK | 404-NOT-VISIBLE | 401-NOT-ENTITLED | 403-SCP-DENY
#                | TIMEOUT | NO-AMZN-CONFIG | NO-CODEX | UNKNOWN
set -u

MODEL="${1:-openai.gpt-6-astra}"
REGION="${2:-us-west-2}"
CODEX="$HOME/.toolbox/bin/codex"
CFG="$HOME/.config/amzn-openaicodex/config.toml"

[ -x "$CODEX" ] || { echo NO-CODEX; exit 0; }
[ -f "$CFG" ]   || { echo NO-AMZN-CONFIG; exit 0; }

BACKUP="$(mktemp)"
cp -p "$CFG" "$BACKUP"
trap 'cp -p "$BACKUP" "$CFG"; rm -f "$BACKUP"' EXIT INT TERM

printf 'bedrock_provider = "runtime"\n' >> "$CFG"

out=$(timeout 90 "$CODEX" exec \
    --profile astra \
    --model "$MODEL" \
    --config "model_providers.amazon-bedrock.aws.region=\"$REGION\"" \
    --skip-git-repo-check --ephemeral --sandbox read-only --cd /tmp --json \
    'Reply exactly OK. Do not call tools.' </dev/null 2>&1)
rc=$?

if [ $rc -eq 124 ]; then
    echo TIMEOUT
    exit 0
fi

case "$out" in
    *'"agent_message"'*'"text":"OK"'*)  echo OK ;;
    *'does not exist'*)                 echo 404-NOT-VISIBLE ;;
    *'not available for this account'*) echo 401-NOT-ENTITLED ;;
    *'explicit deny'*|*'denied by SCP'*) echo 403-SCP-DENY ;;
    *)                                  echo UNKNOWN ;;
esac
