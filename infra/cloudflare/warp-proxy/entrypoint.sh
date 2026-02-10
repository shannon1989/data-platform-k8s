#!/bin/bash
set -e

cd /etc/wireguard

if [ ! -f wgcf-account.toml ]; then
  wgcf register --accept-tos
fi

wgcf generate

# wg-quick 需要 wgcf.conf
mv wgcf-profile.conf wgcf.conf

# 🚑 kind / 容器环境强烈建议禁 IPv6 默认路由
sed -i '/::\/0/d' wgcf.conf

# 禁用 wg-quick 的 DNS / resolvconf 行为
sed -i '/^DNS/d' wgcf.conf
sed -i '/resolvconf/d' wgcf.conf

# 🔑 Squid 自身流量打 fwmark，避免代理自己
# iptables -t mangle -A OUTPUT -m owner --uid-owner proxy -j MARK --set-mark 51820

wg-quick up wgcf

# NAT 所有流量进 WARP
iptables -t nat -A POSTROUTING -o wgcf -j MASQUERADE

# squid config (最简)
cat > /etc/squid/squid.conf <<EOF
http_port 3128
acl all src all
http_access allow all
EOF

exec squid -N
