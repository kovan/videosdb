#!/bin/bash
# all this for debian
sudo apt-get update
sudo apt install -y zsh curl wget tmux git fzf vim net-tools apt-file netcat nmap
sudo apt install -y firefox-esr
sudo apt-file update

#oh my zsh

sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

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

#node

curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - &&\
sudo apt-get install -y nodejs
#poetry
sudo apt install python3-distutils
curl -sSL https://install.python-poetry.org | python3 -


#other
mkdir -p ~/prj
sudo node install -g yarn
cd prj
git clone https://github.com/kovan/dotfiles
cp zshrc ~/.zshrc
source ~/.zshrc

git config --global user.name kovan
git config --global user.email "you@example.com"
ssh-keygen