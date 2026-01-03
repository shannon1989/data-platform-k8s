

5. Deploy Metabase with PostgreSQL as metadata
  1. create metabase namespace
  2. create helm chart
  3. install chart
  ```bash
  helm upgrade --install metabase ./metabase -n metabase
  ```
  4. Check status
  ```bash
  kubectl get pods -n metabase
  kubectl get svc -n metabase
  ```
  5. Access Metabase (port-forward)

  6. add ClickHouse database
    1. login clickhouse
    ```bash
    kubectl exec -it -n clickhouse-operator chi-analytics-ch-analytics-0-0-0 -- clickhouse-client
    ```

    创建 Metabase 用户（推荐 SQL）
    ```sql
    CREATE USER IF NOT EXISTS metabase
    IDENTIFIED WITH sha256_password BY 'metabase_password'
    HOST ANY;
    ```