#!/bin/bash

git submodule sync
git submodule update --init --recursive

# Homebrew + everything in the Brewfile (formulae, cargo, uv tools)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
brew update
brew bundle

# Neovim plugins via lazy.nvim
nvim --headless "+Lazy! sync" +qa

# Cargo + zenith (not packaged in brew with nvidia feature)
curl https://sh.rustup.rs -sSf | sh -s -- -y
~/.cargo/bin/cargo install --features nvidia --git https://github.com/bvaisvil/zenith.git
~/.cargo/bin/cargo install-update -a

# Start assistant with /claudeclaw:start
claude plugin marketplace add moazbuilds/claudeclaw
claude plugin install claudeclaw

toolbox install aim
aim mcp install quicksight-mcp
claude mcp add --scope user quicksight-mcp /local/home/quennv/.aim/mcp-servers/quicksight-mcp

toolbox install AndesCli
aim mcp install andes-mcp

# CloudWatch agent with GPU metrics
# https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Agent-commandline-fleet.html
sudo yum install -y amazon-cloudwatch-agent
sudo tee /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOM'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "root"
    },
    "metrics": {
        "namespace": "Custom/GPU",
        "append_dimensions": {
            "AutoScalingGroupName": "${aws:AutoScalingGroupName}",
            "ImageId": "${aws:ImageId}",
            "InstanceId": "${aws:InstanceId}",
            "InstanceType": "${aws:InstanceType}"
        },
        "aggregation_dimensions": [["InstanceId"]],
        "metrics_collected": {
            "nvidia_gpu": {
                "measurement": ["utilization_gpu", "utilization_memory"]
            }
        }
    }
}
EOM
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status
