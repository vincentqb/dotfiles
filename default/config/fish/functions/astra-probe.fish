function astra-probe --description 'Probe GPT-6 family model IDs and regions through Toolbox Codex'
    # State as of 2026-09-23: Astra is GA on Bedrock (2026-09-08) but BOTH Bedrock
    # surfaces are shut for the shared Caminus accounts -- Mantle answers
    # 401-SCP-DENY in every region, and the documented `bedrock_provider = "runtime"`
    # switch answers 403-SCP-DENY (us-west-2) / 404 (CRIS ids), while the control
    # passes. BuilderHub calls Astra "under evaluation, not generally available";
    # ticket P508665146 says capacity, no ETA. GPT-6 Sol and Luna launched publicly
    # 2026-09-22 (openai.com/index/introducing-gpt-6-sol-and-luna) and are already
    # live on Bedrock for PERSONAL accounts (#openai-codex-internal-interest,
    # 2026-09-22), so the probe now covers them too. The probe exists to catch the
    # flip: any OK on a verified-id, global-cris or runtime-provider row means
    # shared-creds access opened. Until then the only working path is BYOA (see
    # astra.config.toml).
    set --local codex "$HOME/.toolbox/bin/codex"
    set --local prompt 'Reply exactly OK. Do not call tools.'
    set --local dry_run false

    if contains -- --dry-run $argv
        set dry_run true
    end

    if not test -x "$codex"
        echo "Toolbox Codex not found at $codex" >&2
        return 127
    end

    set --local probes \
        'control|openai.gpt-5.6-sol|us-east-2' \
        'verified-id|openai.gpt-6-astra|us-east-1' \
        'verified-id|openai.gpt-6-astra|us-east-2' \
        'verified-id|openai.gpt-6-astra|us-west-2' \
        'verified-id|openai.gpt-6-sol|us-east-2' \
        'verified-id|openai.gpt-6-luna|us-east-2' \
        'global-cris|global.openai.gpt-6-astra|us-east-1'
    set --local timeout_command
    if command --query timeout
        set timeout_command timeout 90
    else if command --query gtimeout
        set timeout_command gtimeout 90
    end

    printf '%-16s %-30s %-11s %s\n' KIND MODEL REGION RESULT
    set --local astra_available false

    for probe in $probes
        set --local fields (string split '|' -- "$probe")
        set --local kind $fields[1]
        set --local model $fields[2]
        set --local region $fields[3]

        if $dry_run
            printf '%-16s %-30s %-11s %s\n' "$kind" "$model" "$region" DRY-RUN
            continue
        end

        set --local cmd "$codex" exec \
            --profile astra \
            --model "$model" \
            --config "model_providers.amazon-bedrock.aws.region=\"$region\"" \
            --skip-git-repo-check \
            --ephemeral \
            --sandbox read-only \
            --cd /tmp \
            --json \
            "$prompt"
        set --local output (command $timeout_command $cmd </dev/null 2>&1)
        set --local exit_code $status
        set --local joined (string join '\n' -- $output)
        set --local result "exit-$exit_code"

        if string match --quiet --regex '"agent_message".*"text":"OK"' "$joined"
            set result OK
            if string match --quiet '*gpt-6*' "$model"
                set astra_available true
            end
        else if string match --quiet '*does not exist*' "$joined"
            set result 404-NOT-VISIBLE
        else if string match --quiet '*not available for this account*' "$joined"
            set result 401-NOT-ENTITLED
        else if string match --quiet '*explicit deny*' "$joined"
            set result 401-SCP-DENY
        else if string match --quiet '*failed to create temporary file for AWS config*' "$joined"
            set result SANDBOX-BLOCKED
        else if test $exit_code -eq 124
            set result TIMEOUT
        end

        printf '%-16s %-30s %-11s %s\n' "$kind" "$model" "$region" "$result"
    end

    # The Mantle rows above all ride `model_provider = "amazon-bedrock"`. The other
    # Bedrock surface is reachable only by flipping `bedrock_provider` in the
    # Amazon-specific config, which has no -c or env override -- delegated to a
    # helper that restores the file under a trap.
    set --local runtime_probe "$HOME/.codex/astra-runtime-probe.sh"
    if $dry_run
        printf '%-16s %-30s %-11s %s\n' runtime-provider openai.gpt-6-astra us-west-2 DRY-RUN
    else if test -x "$runtime_probe"
        set --local runtime_result (bash "$runtime_probe" openai.gpt-6-astra us-west-2)
        printf '%-16s %-30s %-11s %s\n' runtime-provider openai.gpt-6-astra us-west-2 "$runtime_result"
        if test "$runtime_result" = OK
            set astra_available true
        end
    else
        printf '%-16s %-30s %-11s %s\n' runtime-provider openai.gpt-6-astra us-west-2 NO-HELPER
    end

    # Kiro ids drop the vendor prefix (gpt-5.6-sol, not openai.gpt-5.6-sol), so
    # match any model_id containing gpt-6 rather than guessing the exact form.
    set --local model_json (kiro-cli chat --list-models --format json 2>/dev/null)
    set --local kiro_hits (string match --all --regex '"model_id":"[^"]*gpt-6[^"]*"' "$model_json")
    if set --query kiro_hits[1]
        for hit in $kiro_hits
            printf '%-16s %-30s %-11s %s\n' kiro-catalog (string replace --all '"' '' (string split ':' -- "$hit")[2]) N/A AVAILABLE
        end
        set astra_available true
    else
        printf '%-16s %-30s %-11s %s\n' kiro-catalog 'gpt-6*' N/A NOT-LISTED
    end

    if $dry_run; or $astra_available
        return 0
    end
    return 1
end
