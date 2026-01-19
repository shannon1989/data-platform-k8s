import requests
import json
from confluent_kafka import Producer
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

API_URL = "https://fullnode.mainnet.sui.io"
COIN_TYPE = "0xdeeb7a4662eec9f2f3def03fb937a663dddaa2e215b8078a284d026b7946c270::deep::DEEP"
KAFKA_BROKER = 'kafka:9092'

# 构造 JSON-RPC 请求 payload
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "suix_getTotalSupply",
    "params": [COIN_TYPE]
}

def fetch_data():
    # 发送 POST 请求
    try:
        response = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=payload)
        response.raise_for_status()  # 如果请求失败会抛出异常
        data = response.json()
        return data.get("result")
        # print("Total Supply:", result)
    except requests.exceptions.RequestException as e:
        print("请求错误:", e)
    except Exception as e:
        print("解析响应时发生错误:", e)

# send to kafka
def stream_to_kafka(result):
    def delivery_report(err, msg):
        if err is not None:
            print(f"❌ Message delivery failed: {err}")
        else:
            print(f"✅ Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

    producer = Producer({
        'bootstrap.servers': KAFKA_BROKER
    })

    producer.produce(
        topic="deep_total_supply",
        # key=datetime.now().strftime("%Y%m%d%H%M%S"),
        value=json.dumps(result),
        callback=delivery_report
    )

    producer.flush()

    

def fetch_and_push():
    try:
        result = fetch_data()
        print("Starting data streaming...")
        stream_to_kafka(result)
        print("Data streamed successfully to Kafka topic 'deep_total_supply'.")
    except Exception as e:
        print(f"Error during streaming: {e}")
        raise

default_args = {
    'owner': 'mike',
    'description' : 'Retrieve deep total supply from sui API',
    'start_date': datetime.utcnow(),
    'catchup' : False,
}

dag = DAG('deep-api-kafka',
         default_args=default_args,
         schedule=timedelta(minutes=1),
         catchup=False,
         tags=['sui', 'kafka']
         )

with dag:
    task1 = PythonOperator(
        task_id='deep_supply_producer',
        python_callable=fetch_and_push
    )
    #task2

