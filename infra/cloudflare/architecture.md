```mermaid
flowchart LR
    subgraph Internet["🌍 Internet / Users"]
        U[User Browser]
    end

    subgraph CF["☁️ Cloudflare Edge"]
        CFWAF[WAF / Access / Zero Trust]
        CFTunnel[Cloudflare Tunnel<br/>(Argo Tunnel)]
        WARPNet[WARP Network<br/>(Anycast)]
    end

    subgraph Server["🖥️ Ubuntu Server"]
        direction TB

        subgraph WARPClient["🔐 WARP Client"]
            WarpSvc[warp-svc<br/>Full Tunnel]
        end

        subgraph K8s["☸️ Kubernetes Cluster"]
            Ingress[Ingress Controller<br/>(nginx)]
            Grafana[Grafana Pod]
            Prometheus[Prometheus Pod]
            OtherPods[Other Workloads]
        end
    end

    %% Incoming traffic (Cloudflare Tunnel)
    U -->|HTTPS| CFWAF
    CFWAF -->|Access Allowed| CFTunnel
    CFTunnel -->|QUIC / HTTP2| Ingress

    Ingress --> Grafana
    Ingress --> Prometheus
    Ingress --> OtherPods

    %% Outgoing traffic (WARP)
    Grafana -->|Egress| WarpSvc
    Prometheus -->|Egress| WarpSvc
    OtherPods -->|Egress| WarpSvc
    WarpSvc -->|Encrypted Tunnel| WARPNet --> Internet

    %% Notes
    CFTunnel -. "Inbound Only\n(No bulk data)" .-> Ingress
    WarpSvc -. "Outbound Only\n(Fair Use)" .-> WARPNet
  ```