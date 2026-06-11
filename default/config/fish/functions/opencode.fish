function opencode --description 'opencode wrapper: refreshes AWS creds from the toolbox helper for @ai-sdk/amazon-bedrock'
    aws-toolbox-export >/dev/null
    or echo 'opencode: AWS creds refresh failed; opencode may still work if AWS_BEARER_TOKEN_BEDROCK is set' >&2
    command opencode $argv
end
