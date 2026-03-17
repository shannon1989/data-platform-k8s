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
newgrp docker
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
**validate git config**
```bash
ssh -T git@github.com
```

**install vime(nano 是逃生艇，vim 是航母)**
```bash
sudo apt install -y vim
```
_-y: "Do you want to continue? [Y/n]" - enter yes automatically_

**update sshd_config**
```bash
sudo vim /etc/ssh/sshd_config
# or
sudo vim /etc/ssh/sshd_config.d/99-custom.conf
# add below
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
# check
sudo sshd -T | grep -E 'passwordauthentication|pubkeyauthentication'
cat id_ed25519.pub > authorized_keys
```
```bash
# reload service
sudo systemctl reload ssh
```

**Fail2ban**
```bash
# install
sudo apt install fail2ban -y
# start
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

**k8s preparation**
```bash
# chrony
sudo apt install chrony -y
# close swap
sudo swapoff -a
sudo sed -i '/swap/d' /etc/fstab

# kernel parameter
sudo tee /etc/sysctl.d/k8s.conf <<EOF
vm.max_map_count=262144
fs.file-max=1000000
net.core.somaxconn=65535
EOF

# load
sudo sysctl --system
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

### kube-proxy error
"command failed" err="failed complete: too many open files" to create fsnotify watcher: too many open filesstream closed: EOF for kube-system/kube-proxy-vkr6t (kube-proxy)

```bash
# fd
sudo tee /etc/security/limits.d/99-k8s.conf << 'EOF'
* soft nofile 1048576
* hard nofile 1048576
root soft nofile 1048576
root hard nofile 1048576
EOF

# inotify
sudo tee /etc/sysctl.d/99-k8s-inotify.conf << 'EOF'
fs.inotify.max_user_watches=1048576
fs.inotify.max_user_instances=8192
fs.inotify.max_queued_events=65536
EOF

# apply
sudo sysctl --system

# re-login
exit
ssh mike@your_vm

# confirm
ulimit -n

# retart Docker + kind nodes
sudo systemctl restart docker
docker start $(docker ps -aq --filter "name=kind")
```

## ingress config
### install ingress-nginx
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
```
```bash
# add label
kubectl label node kind-control-plane ingress=nginx
```
```bash
# confirm
kubectl get nodes --show-labels | grep ingress
```
```bash
# install ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  -n ingress-nginx \
  --create-namespace \
  -f ingress-nginx-values.yaml
```

```TXT
浏览器
  ↓
宿主机 80 / 443
  ↓  （kind extraPortMappings）
kind control-plane 容器 (30080 / 30443)
  ↓
Ingress Controller（Pod）
  ↓
ClusterIP Service
  ↓
应用 Pod
```


## DockerHub push
### login
docker login

### build
docker build -t cooldina/web3-stream-ingestion:1.1.0 .

### push
docker push cooldina/web3-stream-ingestion:1.1.0