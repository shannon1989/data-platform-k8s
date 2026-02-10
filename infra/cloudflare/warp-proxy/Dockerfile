FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
      curl \
      iproute2 \
      iptables \
      wireguard \
      squid \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# install wgcf
RUN curl -L https://github.com/ViRb3/wgcf/releases/download/v2.2.15/wgcf_2.2.15_linux_amd64 \
    -o /usr/local/bin/wgcf && \
    chmod +x /usr/local/bin/wgcf

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
