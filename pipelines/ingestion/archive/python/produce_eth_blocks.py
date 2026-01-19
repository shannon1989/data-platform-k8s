import time
import json
import requests
from datetime import datetime, timedelta, timezone

BASE_URL = 'https://api.etherscan.io/v2/api?chainid=1'

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

def date_to_timestamp(date_str: str, end: bool = False) -> int:
    """
    date_str: 'YYYY-MM-DD'
    end=False  -> current day 00:00:00
    end=True   -> next day 00:00:00
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    dt = dt.replace(tzinfo=timezone.utc)

    if end:
        dt = dt + timedelta(days=1)

    return int(dt.timestamp())

def get_block_no_by_time(unix_timestamp, max_retries=3):
    params = {'module': 'block', 
            'action': 'getblocknobytime', 
            'timestamp': unix_timestamp,
            'closest': 'after',
            'apikey': ETHERSCAN_API_KEY,
            }
    attempt = 0
    while attempt < max_retries:
        try:
            res = requests.get(BASE_URL, params=params, timeout=10)
            res.raise_for_status()
            json_data = res.json()
            result = json_data.get('result', None)
            return int(result)
        except Exception as e:
            print(f"❌ Error fetching block number : {e}")
            attempt += 1
            time.sleep(2)
    print(f"Error: Failed to fetch block number after {max_retries} retries, skipping.")
    return None

# start_timestamp, 'closest': 'after'
# end_timestamp, 'closest': 'before'

start_date = '2026-01-01'
end_date = '2026-01-02'
start_timestamp = date_to_timestamp(start_date, end=False)
end_timestamp = date_to_timestamp(end_date, end=False)
print("start_block_no: ", get_block_no_by_time(unix_timestamp=start_timestamp))
print("end_block_no: ", get_block_no_by_time(unix_timestamp=end_timestamp))



# producer = Producer({'bootstrap.servers': KAFKA_BROKER})

# def delivery_report(err, msg):
#     if err is not None:
#         print(f"❌ Block delivery failed: {err}")
#     else:
#         print(f"✅ Block {msg.key().decode()} delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

# def get_latest_block_number():
#     params = {'module': 'proxy', 'action': 'eth_blockNumber', 'apikey': ETHERSCAN_API_KEY}
#     try:
#         res = requests.get(BASE_URL, params=params, timeout=10)
#         res.raise_for_status()
#         json_data = res.json()
#         if json_data.get('result'):
#             return int(json_data['result'], 16)
#         else:
#             print(f"Warning: get_latest_block_number got no result: {json_data}")
#             return None
#     except Exception as e:
#         print(f"❌ Failed to get latest block number: {e}")
#         return None

# def get_block_by_number(block_number, max_retries=3):
#     params = {
#         'module': 'proxy',
#         'action': 'eth_getBlockByNumber',
#         'tag': hex(block_number),
#         'boolean': 'true',
#         'apikey': ETHERSCAN_API_KEY
#     }
#     attempt = 0
#     while attempt < max_retries:
#         try:
#             res = requests.get(BASE_URL, params=params, timeout=10)
#             res.raise_for_status()
#             json_data = res.json()
#             result = json_data.get('result', None)
#             if isinstance(result, dict):
#                 return result
#             else:
#                 print(f"Warning: Block {block_number} returned non-dict result: {result}")
#                 attempt += 1
#                 time.sleep(2)
#         except Exception as e:
#             print(f"❌ Error fetching block {block_number}: {e}")
#             attempt += 1
#             time.sleep(2)
#     print(f"Error: Failed to fetch block {block_number} after {max_retries} retries, skipping.")
#     return None

# def fetch_and_push():
#     last_block = None
#     while True:
#         latest_block = get_latest_block_number()
#         if latest_block is None:
#             time.sleep(3)
#             continue
#         if last_block is None:
#             last_block = latest_block - 1
#         while last_block < latest_block:
#             block = get_block_by_number(last_block)
#             if block is None:
#                 last_block += 1
#                 continue
#             block_info = {k: v for k, v in block.items() if k != 'transactions'}
#             block_number_dec = int(block.get('number'), 16) if block.get('number') else None
#             key = str(block_number_dec) if block_number_dec is not None else None

#             try:
#                 producer.produce(
#                     TOPIC_BLOCK,
#                     key=key,
#                     value=json.dumps(block_info)
#                     callback=delivery_report
#                 )
#             except Exception as e:
#                 print(f"❌ Failed to produce block message for block {last_block}: {e}")

#             producer.flush()
#             print(f"Block {last_block} info sent")
#             last_block += 1
#         time.sleep(1)

# fetch_and_push()