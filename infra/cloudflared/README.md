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
