Resume = 有边界、有尽头的 backfill job

Realtime = 无状态、永远追 head 的 daemon job

1️⃣ Resume Job（Backfill / Recover）
用途
- 补历史
- 恢复失败区间
- 一次性 or 有终点

| 维度                     | Resume             |
| ---------------------- | ------------------ |
| 是否读 state              | ✅ 必须               |
| 起点                     | checkpoint + 1     |
| 终点                     | 启动时的 chain head    |
| 是否追新块                  | ❌ 不追               |
| Job 生命周期               | 有终点                |
| Kafka transactional.id | 固定                 |
| State 写入               | running → finished |


2️⃣ Realtime Job（Streaming Daemon）

用途
- 永远追链
- 不补历史
- 高可用

| 维度                     | Realtime      |
| ---------------------- | ------------- |
| 是否读 state              | ❌ 不读          |
| 起点                     | chain head    |
| 终点                     | 无             |
| 是否追新块                  | ✅ 永远          |
| Job 生命周期               | 常驻            |
| Kafka transactional.id | 固定（按 chain）   |
| State 写入               | 只写心跳 / latest |


| 场景     | Tailing    | Bounded |
| ------ | ---------- | ------- |
| 链停止出块  | 暂停         | 暂停      |
| 链继续出块  | 继续         | ❌ 不继续   |
| 跑完历史   | 不结束        | ✅ 结束    |
| 适合 K8s | Deployment | Job     |
