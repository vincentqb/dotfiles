function byoa-probe --description 'Probe the 2026-09 Bedrock model wave through the shared Cecelia account'
    # Watches the OTHER gate from astra-probe: astra-probe asks whether the
    # TOOLBOX codex path (Caminus accounts, Mantle + runtime providers) can see
    # GPT-6; this probes whether the Bedrock account the BYOA rails ride --
    # cecelia-prod 175342148895, role CeceliaAmazonInternal, reached via aws
    # profile l3m-bedrock-process -- may invoke the 2026-09 wave. As of
    # 2026-09-23 the role's identity policy stops at the opus-5 generation:
    # control passes, every new row is DENIED. The flip event is ide-team
    # updating that policy (or a true personal account landing in ~/.aws).
    #
    # Each probe is one Converse call capped at 1 output token: fractions of a
    # cent, billed to the shared account. Exit 0 = at least one new model OK.
    set --local profile l3m-bedrock-process
    # us-west-2, not us-east-1: the Cecelia role policy is REGION-CONDITIONED.
    # The control model answers from us-west-2 and is AccessDenied from
    # us-east-1 (verified 2026-09-23). CRIS routes to capacity cross-region,
    # so probing the entitled region still detects a policy flip for models
    # served elsewhere (Opus 5.5 capacity is us-east-1 for now).
    set --local region us-west-2
    set --local dry_run false
    if contains -- --dry-run $argv
        set dry_run true
    end

    # kind|model-id. CRIS ids measured 2026-09-23 via
    # `aws bedrock list-inference-profiles --region us-east-1` (all ACTIVE).
    # Controls are entitled today and validate creds+region+plumbing; "new"
    # rows are the still-denied wave this probe exists to watch. Not probed:
    # entitled sonnet-5/sonnet-4-6/fable-5 (proven 2026-09-23), and fable-5-1,
    # which carries an EXPLICIT deny on this role — deliberate, never expected
    # to flip, and probing it would only add noise.
    set --local probes \
        'control|us.anthropic.claude-opus-5' \
        'new|global.anthropic.claude-opus-5-5' \
        'new|us.anthropic.claude-opus-5-5' \
        'new|us.openai.gpt-6-sol' \
        'new|us.openai.gpt-6-luna' \
        'new|us.openai.gpt-6-astra' \
        'new|us.openai.gpt-5.6-sol' \
        'new|us.moonshotai.kimi-k3'

    printf '%-9s %-36s %s\n' KIND MODEL RESULT
    set --local flipped false
    for probe in $probes
        set --local fields (string split '|' -- "$probe")
        set --local kind $fields[1]
        set --local model $fields[2]
        if $dry_run
            printf '%-9s %-36s %s\n' "$kind" "$model" DRY-RUN
            continue
        end
        set --local output (aws bedrock-runtime converse \
            --profile "$profile" --region "$region" \
            --model-id "$model" \
            --messages '[{"role":"user","content":[{"text":"hi"}]}]' \
            --inference-config '{"maxTokens":1}' --output json 2>&1)
        set --local joined (string join ' ' -- $output)
        set --local result UNKNOWN
        if string match --quiet '*stopReason*' "$joined"
            set result OK
            if test "$kind" = new
                set flipped true
            end
        else if string match --quiet '*AccessDenied*' "$joined"
            set result DENIED
        else if string match --quiet '*ValidationException*' "$joined"
            set result BAD-ID
        else if string match --quiet '*Throttling*' "$joined"
            set result THROTTLED
        else if string match --quiet '*ExpiredToken*' "$joined"
            set result EXPIRED-CREDS
        end
        printf '%-9s %-36s %s\n' "$kind" "$model" "$result"
    end

    if $dry_run; or $flipped
        return 0
    end
    return 1
end
