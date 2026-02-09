| 组件                | UI / 接口     | Pod 内端口 | Service Port | NodePort  | 宿主机访问端口   | 访问方式                                             |
| ----------------- | ----------- | ------- | ------------ | --------- | --------- | ------------------------------------------------ |
| **Grafana**       | Web UI      | 3000    | 80           | **30000** | **3000**  | [http://localhost:3000](http://localhost:3000)   |
| **Prometheus**    | Web UI      | 9090    | 9090         | **30090** | **9090**  | [http://localhost:9090](http://localhost:9090)   |
| **Kafka UI**      | Web UI      | 8080    | 8080         | **30080** | **8080**  | [http://localhost:8080](http://localhost:8080)   |
| **MinIO Console** | Web UI      | 9001    | 9001         | **30001** | **9001**  | [http://localhost:9001](http://localhost:9001)   |
| **MinIO API**     | S3 API      | 9000    | 9000         | **30002** | **9000**  | [http://localhost:9000](http://localhost:9000)   |
| **ClickHouse**    | HTTP        | 8123    | 8123         | **30123** | **8123**  | [http://localhost:8123](http://localhost:8123)   |
| **Spark UI**      | Driver UI   | 4040    | 4040         | **30404** | **4040**  | [http://localhost:4040](http://localhost:4040)   |
| **Spark History** | History UI  | 18080   | 18080        | **30018** | **18080** | [http://localhost:18080](http://localhost:18080) |
| **Airflow**       | Web UI      | 8080    | 8080         | **30088** | **8088**  | [http://localhost:8088](http://localhost:8088)   |
| **Trino**         | Web UI      | 8080    | 8080         | **30081** | **8081**  | [http://localhost:8081](http://localhost:8081)   |
| **Jupyter**       | Notebook UI | 8888    | 8888         | **30888** | **8888**  | [http://localhost:8888](http://localhost:8888)   |


ingress:
```TXT
浏览器
  ↓
宿主机 80 / 443
  ↓  （kind extraPortMappings）
kind control-plane 容器
  ↓
Ingress Controller（Pod）
  ↓
ClusterIP Service
  ↓
应用 Pod
```


```TXT
grafana.smqj.cc      prometheus.smqj.cc
        │                     │
        └────── Cloudflare ───┘
                     │
              cloudflared tunnel
                     │
        Ubuntu Server（内网）
                     │
        Ingress-NGINX (80)
                     │
      /grafana      /prometheus
         │               │
     Grafana         Prometheus
```