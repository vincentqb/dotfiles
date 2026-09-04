function astra-probe --description 'Probe GPT-6 Astra model IDs and regions through Toolbox Codex'
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
        'openai-slug|gpt-6-astra|us-east-1' \
        'bare-alias|astra|us-east-1' \
        'codex-flag-slug|openai.gpt-6-astra-aeon|us-east-1'
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
            if test "$model" = openai.gpt-6-astra
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

    set --local model_json (kiro-cli chat --list-models --format json 2>/dev/null)
    for model in openai.gpt-6-astra gpt-6-astra astra
        if string match --quiet "*\"model_id\":\"$model\"*" "$model_json"
            printf '%-16s %-30s %-11s %s\n' kiro-catalog "$model" N/A AVAILABLE
        else
            printf '%-16s %-30s %-11s %s\n' kiro-catalog "$model" N/A NOT-LISTED
        end
    end

    if $dry_run; or $astra_available
        return 0
    end
    return 1
end
