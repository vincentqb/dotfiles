function aws-toolbox-export --description 'Export AWS creds from the toolbox claude helper into the current shell'
    if not test -x ~/bin/aws-creds-toolbox
        echo 'aws-toolbox-export: ~/bin/aws-creds-toolbox missing' >&2
        return 1
    end
    set -l creds (~/bin/aws-creds-toolbox)
    or begin
        echo 'aws-toolbox-export: helper failed to produce credentials' >&2
        return 1
    end
    set -gx AWS_ACCESS_KEY_ID     (echo $creds | python3 -c 'import json,sys;print(json.load(sys.stdin)["AccessKeyId"])')
    set -gx AWS_SECRET_ACCESS_KEY (echo $creds | python3 -c 'import json,sys;print(json.load(sys.stdin)["SecretAccessKey"])')
    set -gx AWS_SESSION_TOKEN     (echo $creds | python3 -c 'import json,sys;print(json.load(sys.stdin)["SessionToken"])')
    set -gx AWS_REGION            us-west-2
    echo 'AWS env vars set; expires '(echo $creds | python3 -c 'import json,sys;print(json.load(sys.stdin)["Expiration"])')
end
