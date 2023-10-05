#!/bin/bash

git submodule sync
git submodule update --init --recursive
~/dotfiles/dot.py/dot.py install default

/usr/bin/pip3 install --user -r requirements.txt --use-feature=2020-resolver

# Install latest neovim
sudo yum install fuse
mkdir -p ~/.local/bin
wget https://github.com/neovim/neovim/releases/download/stable/nvim.appimage -O ~/.local/bin/nvim
chmod +x ~/.local/bin/nvim

# Update nvim plugins
~/.local/bin/nvim --headless +PackClean +qa
~/.local/bin/nvim --headless +PackUpdate +qa
~/.local/bin/nvim --headless +DirtytalkUpdate +qa

sudo yum-config-manager --add-repo https://download.opensuse.org/repositories/shells:fish:release:3/CentOS_7/shells:fish:release:3.repo
sudo yum install fish

curl https://sh.rustup.rs -sSf | sh
~/.cargo/bin/cargo install --locked bat fd-find ripgrep eza
# cargo install --locked bat fd-find ripgrep eza

conda config --set auto_activate_base true

# https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Agent-commandline-fleet.html
sudo yum install amazon-cloudwatch-agent
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
                "measurement": [
                    "utilization_gpu",
                    "utilization_memory"
                ]
            }
        }
    }
}
EOM
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status
