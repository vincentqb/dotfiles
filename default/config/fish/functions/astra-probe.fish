function astra-probe --description 'Probe the GPT-6 family (Astra, Sol, Luna, 6.1 Sol, 6.1 Terra) through Toolbox Codex on Mantle'
    # State as of 2026-10-26: the shared-creds gate OPENED for everything but
    # Astra. Toolbox Codex (>= 0.159.1.602, #openai-codex-internal-interest
    # 2026-09-30) serves GPT-6.1 Sol on Mantle, and this probe found GPT-6 Sol,
    # GPT-6 Luna and GPT-6.1 Terra (launched the same day) answering too -- in
    # us-east-1 ONLY. us-east-2 and us-west-2 return 404 "does not exist" for the
    # whole GPT-6 family, which reads like a bad id and is a region fault (the
    # astra.config.toml trap, now hitting every 6.x id). Astra alone stays
    # 403-SCP-DENY in all three regions (P508665146); OpenAI has shelved GPT-6.1
    # Astra after its own safety review (press, 2026-10-20), so Astra is not
    # the model to wait for. The kiro catalog still has no gpt-6 row: the Kiro
    # team says Bedrock is not providing internal capacity for these models and
    # has no date (#kiro-cli-internal-software-builders, 2026-10-25).
    #
    # History: Astra GA'd on Bedrock 2026-09-08; until 2026-09-30 BOTH Bedrock
    # surfaces were shut for the shared Caminus accounts (Mantle 401-SCP-DENY in
    # every region, the documented `bedrock_provider = "runtime"` switch
    # 403-SCP-DENY / 404), while the control passed. GPT-6 Sol and Luna launched
    # 2026-09-22 and rode Bedrock for personal accounts first (BYOA, see
    # byoa.config.toml). Exit 0 = some gpt-6 row answered; the row that matters
    # now is Astra's -- an OK there is the flip still being watched for.
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

    # All rows ride `--profile astra` for its Mantle provider table; the region
    # is overridden per row. The us-east-2 row is the trap, kept on purpose:
    # it must read 404-NOT-VISIBLE while the us-east-1 row above it reads OK.
    set --local probes \
        'control|openai.gpt-5.6-sol|us-east-1' \
        'verified-id|openai.gpt-6-astra|us-east-1' \
        'verified-id|openai.gpt-6-astra|us-east-2' \
        'verified-id|openai.gpt-6-astra|us-west-2' \
        'verified-id|openai.gpt-6-sol|us-east-1' \
        'verified-id|openai.gpt-6-luna|us-east-1' \
        'verified-id|openai.gpt-6.1-sol|us-east-1' \
        'verified-id|openai.gpt-6.1-terra|us-east-1' \
        'region-trap|openai.gpt-6.1-sol|us-east-2' \
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

        # Match the prefix only: the 6.1 models like to answer "OK." or
        # "OK\n", which a closing-quote anchor turned into a false exit-0 row.
        if string match --quiet --regex '"agent_message".*"text":"OK' "$joined"
            set result OK
            if string match --quiet '*gpt-6*' "$model"; and test "$kind" != region-trap
                set astra_available true
            end
        else if string match --quiet '*does not exist*' "$joined"
            set result 404-NOT-VISIBLE
        else if string match --quiet '*not available for this account*' "$joined"
            set result 401-NOT-ENTITLED
        else if string match --quiet '*explicit deny*' "$joined"
            set result 403-SCP-DENY
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
