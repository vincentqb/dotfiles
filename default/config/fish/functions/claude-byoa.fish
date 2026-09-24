function claude-byoa --description 'Claude Code over the BYOA Bedrock rail (Opus 5.5 and friends, billed to IPC-PCB-Science)'
    # The BYOA rail from #practical-ai 2026-09-23 (kushchyk): --aws-profile swaps
    # the account under toolbox Claude Code, --settings layers availableModels +
    # modelOverrides for models the managed /model picker lacks, region pinned
    # us-east-1 (Opus 5.5 capacity lives there for now).
    #
    # ACCOUNT (since 2026-09-24): aws profile `ipc-pcb-science` — Conduit account
    # IPC-PCB-Science (471112940283), role IibsAdminAccess-DO-NOT-DELETE,
    # ada-vended via credential_process (needs a valid midway session; on auth
    # errors run `mwinit` and retry). This account is FULLY ENTITLED: verified
    # live 2026-09-24, opus-5-5 / gpt-6 sol+luna+astra / kimi-k3 all answer,
    # in both us-east-1 and us-west-2. ⚠ Every turn bills the team science
    # account — this is not the flat-rate builder subscription.
    #
    # History: until 2026-09-24 this rail rode the shared cecelia-prod account,
    # whose curated, us-west-2-only allowlist blocked the whole 2026-09 wave
    # (and still explicitly denies fable-5-1). `byoa-probe` now health-checks
    # the IPC rail instead.
    #
    #   claude-byoa                          # claude-opus-5-5[1m], verified live
    #   claude-byoa claude-sonnet-5          # any row from settings-byoa.json
    #   claude-byoa 'claude-fable-5-1[1m]'   # fable survives kiro's Sep 25 removal here
    set --local model 'claude-opus-5-5[1m]'
    if set --query argv[1]; and not string match --quiet -- '-*' "$argv[1]"
        set model $argv[1]
        set --erase argv[1]
    end
    "$HOME/.toolbox/bin/claude" \
        --aws-profile ipc-pcb-science \
        --settings "$HOME/.claude/settings-byoa.json" \
        --model "$model" \
        $argv
end
