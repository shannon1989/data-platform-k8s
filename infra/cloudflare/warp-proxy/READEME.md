docker build -t wgcf-squid:local .
kind load docker-image wgcf-squid:local

kubectl create ns build
kubectl apply -f warp.yaml


# validate
kubectl exec -n build deploy/warp-proxy -- \
  curl -x http://127.0.0.1:3128 https://www.cloudflare.com/cdn-cgi/trace


# re-deployment
docker build -t wgcf-squid:local .
kind load docker-image wgcf-squid:local
kubectl rollout restart deploy/warp-proxy -n build



# docker proxy
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/http-proxy.conf <<EOF
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:3128"
Environment="HTTPS_PROXY=http://127.0.0.1:3128"
NO_PROXY=localhost,127.0.0.1,::1
EOF


# check proxy log
kubectl exec -n build deploy/warp-proxy -- \ tail -f /var/log/squid/access.log

# remove config
sudo rm /etc/systemd/system/docker.service.d/http-proxy.conf
sudo rmdir /etc/systemd/system/docker.service.d 2>/dev/null || true
sudo systemctl daemon-reexec
sudo systemctl daemon-reload

sudo systemctl restart docker
sudo systemctl show docker --property=Environment
