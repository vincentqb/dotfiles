function codex-byoa --description 'Codex on GPT-6 (sol/luna/astra) through the BYOA Bedrock rail (IPC-PCB-Science)'
    # Why a wrapper and not just `codex --profile byoa`: the profile file's
    # `model_provider = "amazon-bedrock-runtime"` does NOT survive config
    # layering — bare `--profile byoa` still routed to Mantle and died with the
    # misleading 404 "The model 'us.openai.gpt-6-sol' does not exist" from
    # bedrock-mantle.us-east-2 (observed 2026-09-24; same trap class as the
    # astra.config.toml region trap). A `-c` override outranks every layer, and
    # with it the profile's provider table (region us-east-1, aws profile
    # ipc-pcb-science) applies correctly — verified live: sol and astra both
    # answer end-to-end.
    #
    #   codex-byoa                               # GPT-6 Sol
    #   codex-byoa -m us.openai.gpt-6-astra      # the one Mantle still denies
    #   codex-byoa -m us.openai.gpt-6-luna
    # ⚠ Turns bill IPC-PCB-Science (471112940283), not the builder subscription.
    "$HOME/.toolbox/bin/codex" \
        --profile byoa \
        -c 'model_provider="amazon-bedrock-runtime"' \
        $argv
end
