#!/bin/bash
# all this for debian
sudo apt-get update
sudo apt install -y zsh curl wget tmux git fzf vim net-tools apt-file netcat nmap strace ltrace
sudo apt install -y firefox-esr
sudo apt-file update


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
sudo apt install python3-distutils
curl -sSL https://install.python-poetry.org | python3 -

sudo npm i -g firebase-tools
sudo npm i -g yarn

sudo usermod -a -G docker k
git config --global user.name kovan
git config --global user.email "you@example.com"
echo net.ipv4.ping_group_range="0 2147483647" | sudo tee /etc/sysctl.conf

sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
#other
mkdir -p ~/prj
cd prj
git clone https://github.com/kovan/dotfiles
cp zshrc ~/.zshrc
source ~/.zshrc

ssh-keygen

