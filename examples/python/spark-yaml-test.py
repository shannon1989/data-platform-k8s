import yaml
from pathlib import Path
from kubernetes import client, config
import time

# -------------------------------
# 1️⃣ 在 Notebook 里写 PySpark 逻辑
# -------------------------------

pyspark_code = """
from pyspark.sql import SparkSession
from delta.tables import DeltaTable

spark = SparkSession.builder.appName("NotebookSparkJob").getOrCreate()

# 示例数据
data = [("Alice", 30), ("Bob", 25), ("Charlie", 35)]
columns = ["name", "age"]
df = spark.createDataFrame(data, columns)

# 写入 Delta 表到 MinIO
delta_path = "s3a://datalake/bronze/delta-example/"
df.write.format("delta").mode("overwrite").partitionBy("age").save(delta_path)

# 读取 Delta 表
df_read = spark.read.format("delta").load(delta_path)
df_read.show()
"""

# -------------------------------
# 2️⃣ 自动生成 Python 脚本文件
# -------------------------------

script_name = "my_notebook_script.py"
script_path = Path(script_name)
with script_path.open("w") as f:
    f.write(pyspark_code)

print(f"✅ Python 脚本已生成: {script_path.resolve()}")

# -------------------------------
# 3️⃣ 生成 SparkApplication YAML
# -------------------------------

spark_app = {
    "apiVersion": "sparkoperator.k8s.io/v1beta2",
    "kind": "SparkApplication",
    "metadata": {
        "name": "notebook-spark-job",
        "namespace": "spark-operator"
    },
    "spec": {
        "type": "Python",
        "mode": "cluster",
        "image": "docker.io/library/spark:4.0.0",  # 自定义镜像需包含 PySpark + Delta
        "mainApplicationFile": f"local:///opt/spark/app/{script_name}",
        "sparkVersion": "3.5.0",
        "restartPolicy": {"type": "Never"},
        "driver": {
            "cores": 1,
            "memory": "1g",
            "serviceAccount": "spark-operator-spark"
        },
        "executor": {
            "cores": 1,
            "instances": 2,
            "memory": "1g"
        },
        "sparkConf": {
            "spark.hadoop.fs.s3a.endpoint": "http://minio.airflow.svc.cluster.local:9000",
            "spark.hadoop.fs.s3a.access.key": "minioadmin",
            "spark.hadoop.fs.s3a.secret.key": "minioadmin",
            "spark.hadoop.fs.s3a.path.style.access": "true",
            "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
            "spark.sql.extensions": "io.delta.sql.DeltaSparkSessionExtension",
            "spark.sql.catalog.spark_catalog": "org.apache.spark.sql.delta.catalog.DeltaCatalog"
        }
    }
}

yaml_file = Path("spark_app.yaml")
with yaml_file.open("w") as f:
    yaml.dump(spark_app, f)

print(f"✅ SparkApplication YAML 已生成: {yaml_file.resolve()}")

# -------------------------------
# 4️⃣ 使用 Python Kubernetes API 提交 SparkApplication
# -------------------------------

# 在 Pod 内运行，使用 in-cluster config
config.load_incluster_config()
api = client.CustomObjectsApi()

namespace = "spark-operator"
group = "sparkoperator.k8s.io"
version = "v1beta2"
plural = "sparkapplications"

# 创建 SparkApplication
try:
    api.create_namespaced_custom_object(
        group=group,
        version=version,
        namespace=namespace,
        plural=plural,
        body=spark_app
    )
    print("✅ SparkApplication 已提交 (Python API)")
except client.rest.ApiException as e:
    if e.status == 409:
        print("⚠️ SparkApplication 已存在")
    else:
        print("❌ 提交失败:", e)

# -------------------------------
# 5️⃣ 查询 SparkApplication 状态
# -------------------------------

def get_spark_app_status(name):
    try:
        app = api.get_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name
        )
        return app.get("status", {})
    except client.rest.ApiException as e:
        print("❌ 查询失败:", e)
        return None

# 等待 job 完成
app_name = spark_app["metadata"]["name"]
while True:
    status = get_spark_app_status(app_name)
    if status:
        state = status.get("applicationState", {}).get("state")
        print(f"当前状态: {state}")
        if state in ["COMPLETED", "FAILED", "UNKNOWN"]:
            break
    else:
        print("等待状态...")
    time.sleep(5)

print("✅ SparkApplication 执行结束，最终状态:", state)
