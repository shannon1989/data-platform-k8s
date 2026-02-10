# install cloudflared in Ubuntu Server

```bash
# install
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared
```
```bash
# validate
cloudflared version
```

```bash
# login cloudflared
cloudflared tunnel login
# create Tunnel
cloudflared tunnel create k8s-observability
```

```bash
# config cloudflared
sudo mkdir -p /etc/cloudflared
sudo vim /etc/cloudflared/config.yml
```

```YAML
tunnel: abcd-1234-xxxx
credentials-file: /etc/cloudflared/abcd-1234-xxxx.json

ingress:
  - hostname: grafana.smqj.cc
    service: http://localhost:80

  - hostname: prometheus.smqj.cc
    service: http://localhost:80

  - service: http_status:404
```

拷贝凭证文件
sudo cp ~/.cloudflared/abcd-1234-xxxx.json /etc/cloudflared/

创建 DNS 记录（Tunnel 方式）
cloudflared tunnel route dns k8s-observability grafana.your_domain.com
cloudflared tunnel route dns k8s-observability prometheus.your_domain.com

启动 cloudflared（systemd）
1️⃣ 安装为系统服务
sudo cloudflared service install

2️⃣ 启动 & 开机自启
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

3️⃣ 看日志
journalctl -u cloudflared -f

# 查看status
sudo systemctl status cloudflared

# validate rules:
cloudflared --config /etc/cloudflared/config.yml tunnel ingress validate

## Cloudflared k8s Deployment

### Disable systemd
```bash
sudo systemctl stop cloudflared
sudo systemctl disable cloudflared
```

1️⃣ 创建 Secret（放 tunnel 凭证）
```bash
kubectl create namespace cloudflared
kubectl create secret generic cloudflared-credentials \
  -n cloudflared \
  --from-file=credentials.json=/home/mike/.cloudflared/e82b40ae-deed-40c1-9d8c-6d24347c4ca3.json
```
2️⃣ ConfigMap（config.yml）
```bash
kubectl apply -f config.yaml
```

3️⃣ Deployment（高可用）
```bash
kubectl apply -f cloudflared.yaml
```

确认 Tunnel 状态：
```bash
cloudflared tunnel info e82b40ae-deed-40c1-9d8c-6d24347c4ca3
```

kubectl -n cloudflared rollout restart deployment cloudflared


# windows install cloudflared
## powershell
winget install --id Cloudflare.cloudflared

# validate
winget list cloudflared