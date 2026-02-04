如果 job.py 在本地：

kubectl cp bsc_block_txn_cnt.py flink/flink-session-647c9c8d74-9wtn7:/opt/flink/bsc_block_txn_cnt.py
kubectl exec -it -n flink flink-session-647c9c8d74-9wtn7 -- flink run -py /opt/flink/bsc_block_txn_cnt.py

```bash
flink list
flink cancel ef9474a4ef864ce68ce279cca2728b62
```

~/bin/sql-client.sh