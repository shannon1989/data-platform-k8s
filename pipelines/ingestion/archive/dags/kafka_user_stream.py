import json
import requests
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from kafka import KafkaProducer
import time

default_args = {
    'owner': 'mike',
    'start_date': datetime(2025, 7, 2, 11, 30)
}

def fetch_data():
    print("Fetching user data from randomuser.me API...")
    try:
      response = requests.get('https://randomuser.me/api/')
      response.raise_for_status()  # Check if the request was successful
      print("API response received successfully.")
      return response.json()['results'][0]

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        raise
    

def format_data(res):
    location = res['location']
    formatted_data = {
        'first_name': res['name']['first'],
        'last_name': res['name']['last'],
        'gender': res['gender'],
        'address': f"{str(location['street']['number'])} {location['street']['name']} " \
                   f"{location['city']}, {location['state']}, {location['country']}",
        'postcode': location['postcode'],
        'email': res['email'],
        'username': res['login']['username'],
        'dob': res['dob']['date'],
        'registration_date': res['registered']['date'],
        'phone': res['phone'],
        'picture': res['picture']['medium']
    }
    return formatted_data

def main():
  try:
    res = fetch_data()
    res = format_data(res)
    # print(json.dumps(res, indent=2))
    print("Starting data streaming...")
    producer = KafkaProducer(bootstrap_servers='broker:29092',max_block_ms=5000)
    producer.send('user_data', json.dumps(res).encode('utf-8'))
    print("date streamed successfully to Kafka topic 'user_data'.")
  except Exception as e:
    print(f"Error during streaming: {e}")
    raise

dag = DAG('user_automation',
         default_args=default_args,
         schedule=timedelta(minutes=5),
         catchup=False)

with dag:
    task1 = PythonOperator(
        task_id='stream_data',
        python_callable=main
    )
    #task2