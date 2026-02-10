
# WARP is not supported on machines running cloudflared tunnels

# Add cloudflare gpg key
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg


# Add this repo to your apt repositories
echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list


# Install
sudo apt-get update && sudo apt-get install cloudflare-warp

# validate service
sudo systemctl status warp-svc

## 把你的服务器注册到 Cloudflare WARP 网络(只需要一次)
warp-cli registration new

# set mode
warp-cli mode warp

# connect warp
warp-cli connect

# check status
warp-cli status

# 验证出口是否真的走 WARP
curl https://www.cloudflare.com/cdn-cgi/trace
warp=on

# check all setting
warp-cli settings --help

# check mode
warp-cli mode --help

# disconnect
warp-cli disconnect

# disable auto start
sudo systemctl disable warp-svc