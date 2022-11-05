#!/bin/bash
# all this for debian
sudo apt-get update
sudo apt install -y zsh curl wget tmux git fzf vim net-tools apt-file netcat nmap strace ltrace bwm-ng ripgrep htop fd-find aptitude bpytop rsync
sudo apt-file update



sudo usermod -a -G docker k
git config --global user.name kovan
git config --global user.email "you@example.com"
echo net.ipv4.ping_group_range="0 2147483647" | sudo tee /etc/sysctl.conf


#other
mkdir -p ~/prj
cd ~/prj
git clone https://github.com/kovan/dotfiles

sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
cp ~/prj/dotfiles/zshrc ~/.zshrc
source ~/.zshrc


# task
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin


# docker:
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin


echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install google-cloud-cli

#node

curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - &&\
sudo apt-get install -y nodejs
#poetry
sudo apt install python3-distutils -y
curl -sSL https://install.python-poetry.org | python3 -

sudo apt install openjdk-17-jre-headless -y
sudo npm i -g firebase-tools
sudo npm i -g yarn
