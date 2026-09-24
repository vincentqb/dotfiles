function byoa-probe --description 'Health-check the BYOA Bedrock rail (IPC-PCB-Science) across the 2026-09 model wave'
    # Since 2026-09-24 this probes the LIVE rail, not a hoped-for flip: aws
    # profile `ipc-pcb-science` (Conduit IPC-PCB-Science, 471112940283, admin
    # role, ada credential_process) is fully entitled — every row below
    # answered on 2026-09-24. A regression here means lost Conduit
    # authorization, an SCP change, a midway session needing `mwinit`, or a
    # Bedrock catalog revision — the RESULT column tells which.
    #
    # (The original 2026-09-23 version watched the shared cecelia-prod account,
    # whose us-west-2-only allowlist blocked this whole wave; that gate stopped
    # mattering once the IPC account proved out. astra-probe still watches the
    # separate toolbox/Mantle gate, where GPT-6 remains SCP-denied.)
    #
    # Each probe is one Converse call capped at 16 output tokens — the MINIMUM
    # the OpenAI family accepts (maxTokens below 16 is rejected by the model
    # with invalid_request_error, learned the hard way). Fractions of a cent,
    # billed to IPC-PCB-Science. Exit 0 = every row OK.
    set --local profile ipc-pcb-science
    set --local region us-east-1
    set --local dry_run false
    if contains -- --dry-run $argv
        set dry_run true
    end

    # CRIS ids measured 2026-09-23/24 via list-inference-profiles (ACTIVE).
    # fable-5-1 is NOT probed here: raw Converse rejects it over data-retention
    # mode ("data retention mode 'default' is not available") — an expected
    # false alarm, since Claude Code arranges the mode and the claude-byoa rail
    # runs it fine (verified live 2026-09-24).
    set --local probes \
        'anthropic|global.anthropic.claude-opus-5-5' \
        'anthropic|global.anthropic.claude-opus-5' \
        'anthropic|global.anthropic.claude-sonnet-5' \
        'openai|us.openai.gpt-6-sol' \
        'openai|us.openai.gpt-6-luna' \
        'openai|us.openai.gpt-6-astra' \
        'moonshot|global.moonshotai.kimi-k3'

    printf '%-10s %-36s %s\n' KIND MODEL RESULT
    set --local all_ok true
    for probe in $probes
        set --local fields (string split '|' -- "$probe")
        set --local kind $fields[1]
        set --local model $fields[2]
        if $dry_run
            printf '%-10s %-36s %s\n' "$kind" "$model" DRY-RUN
            continue
        end
        set --local output (aws bedrock-runtime converse \
            --profile "$profile" --region "$region" \
            --model-id "$model" \
            --messages '[{"role":"user","content":[{"text":"hi"}]}]' \
            --inference-config '{"maxTokens":16}' --output json 2>&1)
        set --local joined (string join ' ' -- $output)
        set --local result UNKNOWN
        if string match --quiet '*stopReason*' "$joined"
            set result OK
        else if string match --quiet '*AccessDenied*' "$joined"
            set result DENIED
        else if string match --quiet '*ExpiredToken*' "$joined"
            set result EXPIRED-CREDS/mwinit
        else if string match --quiet '*ValidationException*' "$joined"
            set result BAD-REQUEST
        else if string match --quiet '*Throttling*' "$joined"
            set result THROTTLED
        end
        if test "$result" != OK; and test "$result" != THROTTLED
            set all_ok false
        end
        printf '%-10s %-36s %s\n' "$kind" "$model" "$result"
    end

    if $dry_run; or $all_ok
        return 0
    end
    return 1
end
