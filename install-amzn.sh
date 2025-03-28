#!/bin/bash

git submodule sync
git submodule update --init --recursive
/usr/bin/pip3 install --user -r requirements.txt
dot.py link default

# Install latest neovim
sudo yum install -y fuse
mkdir -p ~/.local/bin
wget https://github.com/neovim/neovim/releases/download/stable/nvim.appimage -O ~/.local/bin/nvim
chmod +x ~/.local/bin/nvim

# Update nvim plugins
~/.local/bin/nvim --headless +PackClean +qa
~/.local/bin/nvim --headless +PackUpdate +qa
~/.local/bin/nvim --headless +DirtytalkUpdate +qa

# Install fish
sudo yum-config-manager --add-repo https://download.opensuse.org/repositories/shells:fish:release:3/CentOS_7/shells:fish:release:3.repo
sudo yum install -y fish

# Install utilities like chsh
sudo yum install util-linux-user
sudo chsh -u ec2-user -s /usr/bin/fish

# Install cargo
curl https://sh.rustup.rs -sSf | sh -s -- -y
~/.cargo/bin/cargo install --locked bat fd-find ripgrep eza

# Install zellij
sudo yum install -y perl-IPC-Cmd
~/.cargo/bin/cargo install --locked zellij

# Install zenith
sudo dnf install -y clang
~/.cargo/bin/cargo install --features nvidia --git https://github.com/bvaisvil/zenith.git

# Install wezterm server only
cargo install --branch=main --git https://github.com/wezterm/wezterm.git generate-bidi strip-ansi-escapes wezterm-mux-server
# git clone --depth=1 --branch=main --recursive https://github.com/wezterm/wezterm.git
# cd wezterm
# git submodule update --init --recursive wezterm/
# ./wezterm/get-deps
# cargo build --release --bin wezterm-mux-server
# cp ./wezterm/target/release/wezterm-mux-server ~/.local/bin/
# cd ..

# Install conda
# wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
# bash ~/miniconda.sh -b -p ~/miniconda
# eval "$(~/miniconda/bin/conda shell.bash hook)"
# ~/miniconda/bin/conda init fish
# ~/miniconda/bin/conda init --all
# ~/miniconda/bin/conda init zsh
# ~/miniconda/bin/conda init fish
# ~/miniconda/bin/conda config --set auto_activate_base true
# ~/miniconda/bin/conda config --set changeps1 False
# ~/miniconda/bin/conda update -n base -c conda-forge conda

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

# Install dependecies for efs
sudo yum install -y amazon-efs-utils
sudo mkdir /efs
sudo mount -t efs -o tls,iam fs-9c2846d5 /efs

# Ensure latest nvidia
# sudo dnf install -y kernel-modules-extra
# sudo dnf install -y nvidia-release
# sudo dnf install -y nvidia-driver
# sudo dnf install -y cuda-toolkit
# Check drivers are installed properly
# nvidia-smi
# python -c "import torch; assert torch.cuda.is_available()"
