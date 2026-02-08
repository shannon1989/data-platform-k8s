# Ubuntu k8s setup script
## install docker:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo ./get-docker.sh
<...>
```

### use docker without sudo
```bash
sudo usermod -aG docker $USER
reboot
```

### install helm:
```bash
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4
chmod 700 get_helm.sh
./get_helm.sh
```

### install kubectl:
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
kubectl version --client
which kubectl
```

### install kind:
```bash
[ $(uname -m) = x86_64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.31.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
kind version
```

### install and config openssh:
```bash
sudo apt update
sudo apt install openssh-server
sudo systemctl start ssh
sudo systemctl status ssh
sudo systemctl enable ssh
```

### config ssh rsa key
```bash
ssh-keygen -t ed25519 -C "mike@ubuntuvm"
```
copy id_ed25519 contents to ~/.ssh/authorized_keys


**install vime(nano 是逃生艇，vim 是航母)**
```bash
sudo apt install -y vim
```
_-y: "Do you want to continue? [Y/n]" - enter yes automatically_

**update sshd_config**
```bash
sudo vim /etc/ssh/sshd_config
```
```TXT
PubkeyAuthentication yes
PasswordAuthentication no
```

### config local hostname
```TXT
Host ubuntus
    HostName 192.168.9.103
    User mike
    IdentityFile ~/.ssh/id_ed25519
```

### copy clash to ubuntu:
```bash
scp Clash.Verge_2.3.2_amd64.deb ubuntus:/home/mike/Downloads/
```

### create cluser with kind-cluster.yaml file:
```bash
kind create cluster --name kind --config kind-prod-cluster.yaml
```
### delete cluster
```bash
kind delete cluster --name kind
```
### check nodes:
```bash
kubectl get nodes -o wide
kubectl cluster-info
kubectl describe node <node-name>
```

### install metrics:
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.6.1/components.yaml
```

### config metrics if metrics server failed to run:
```bash
kubectl edit deployment metrics-server -n kube-system
```
```YAML
spec:
  containers:
  - name: metrics-server
    image: k8s.gcr.io/metrics-server/metrics-server:v0.6.1
    args:
    - --kubelet-insecure-tls
```

### validate metrics server:
```bash
kubectl top nodes
```

### install k9s:
```bash
wget https://github.com/derailed/k9s/releases/latest/download/k9s_Linux_amd64.tar.gz
tar -xzf k9s_Linux_amd64.tar.gz
sudo mv k9s /usr/local/bin/
k9s version
```

### install and config git
```bash
# config ssh
ssh-keygen -t ed25519 -C "mike@ubuntuvm"
# cat ~/.ssh/id_ed25519.pub to github -> Settings -> SSH and GPG keys
ssh -T git@github.com
cd ~
git clone git@github.com:shannon1989/data-platform-k8s.git

# config git user info
git config --global user.name "Mike Liang"
git config --global user.email "your_email@example.com"

# validate
git config --global --list
```