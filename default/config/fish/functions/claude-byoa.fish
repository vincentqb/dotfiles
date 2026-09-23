function claude-byoa --description 'Claude Code over the BYOA Bedrock rail (new-wave models when entitled)'
    # The BYOA rail from #practical-ai 2026-09-23 (kushchyk): --aws-profile swaps
    # the account under toolbox Claude Code, --settings layers availableModels +
    # modelOverrides for models the managed /model picker lacks.
    #
    # ⚠ REGION: kushchyk's recipe pins us-east-1 (Opus 5.5 capacity lives there,
    # for personal accounts). On THIS box that pin breaks everything: the shared
    # account's policy is REGION-CONDITIONED — global.anthropic.claude-opus-5
    # answers from us-west-2 and is AccessDenied from us-east-1 (verified
    # 2026-09-23). So settings-byoa.json pins us-west-2; CRIS routes to capacity
    # cross-region once a model is entitled. On a real personal account, flip
    # the pin to us-east-1 per the recipe.
    #
    # ⚠ "BYOA" is aspirational on this box: every AWS profile here (including
    # toolbox's own claude-code-DO-NOT-DELETE) rides the SHARED cecelia-prod
    # science account (175342148895, role CeceliaAmazonInternal, owner ide-team).
    # Its policy is a curated allowlist, us-west-2 only. Verified 2026-09-23:
    #   entitled:  claude-opus-5[1m], claude-opus-4-8[1m], claude-haiku-4-5,
    #              claude-sonnet-5, claude-sonnet-4-6[1m],
    #              claude-fable-5 (throttled but authorized — and this rail keeps
    #              fable-5 reachable after kiro removes it on Sep 25)
    #   no-allow:  claude-opus-5-5[1m] (plus GPT-6/kimi, which ride codex/l3m)
    #   EXPLICIT DENY: claude-fable-5-1[1m] — deliberately blocked on this role,
    #              so do not expect that one to flip
    # Run `byoa-probe` to re-check the edge; when it flips, this launcher works
    # unchanged. With a true personal account, swap the profile below.
    #
    #   claude-byoa                       # claude-opus-5-5[1m] (denied until flip)
    #   claude-byoa 'claude-opus-5[1m]'   # entitled today, end-to-end verified
    set --local model 'claude-opus-5-5[1m]'
    if set --query argv[1]; and not string match --quiet -- '-*' "$argv[1]"
        set model $argv[1]
        set --erase argv[1]
    end
    "$HOME/.toolbox/bin/claude" \
        --aws-profile l3m-bedrock-process \
        --settings "$HOME/.claude/settings-byoa.json" \
        --model "$model" \
        $argv
end
