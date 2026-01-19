from airflow import DAG
from datetime import datetime, timedelta
from airflow.providers.standard.operators.python import PythonOperator
import requests
import psycopg2


api_key = "2d4b8910a0d79235267c0cdd94169b1b"
api_url = f"http://api.weatherstack.com/current?access_key={api_key}&query=Shanghai"

def fetch_data():
  print("Fetching weather data from WeatherStack API...")
  try:
    response = requests.get(api_url)
    response.raise_for_status()
    print("API response received successfully.")
    return response.json()
  except requests.exceptions.RequestException as e:
    print(f"An error occured: {e}")
    raise

def mock_fecth_data():
  return {'request': {'type': 'City', 'query': 'Shanghai, China', 'language': 'en', 'unit': 'm'}, 'location': {'name': 'Shanghai', 'country': 'China', 'region': 'Shanghai', 'lat': '31.005', 'lon': '121.409', 'timezone_id': 'Asia/Shanghai', 'localtime': '2025-06-27 15:46', 'localtime_epoch': 1751039160, 'utc_offset': '8.0'}, 'current': {'observation_time': '07:46 AM', 'temperature': 38, 'weather_code': 263, 'weather_icons': ['https://cdn.worldweatheronline.com/images/wsymbols01_png_64/wsymbol_0009_light_rain_showers.png'], 'weather_descriptions': ['Patchy light drizzle'], 'astro': {'sunrise': '04:53 AM', 'sunset': '07:02 PM', 'moonrise': '06:21 AM', 'moonset': '08:58 PM', 'moon_phase': 'Waxing Crescent', 'moon_illumination': 3}, 'air_quality': {'co': '906.5', 'no2': '121.36', 'o3': '25', 'so2': '59.385', 'pm2_5': '100.27', 'pm10': '100.64', 'us-epa-index': '4', 'gb-defra-index': '4'}, 'wind_speed': 6, 'wind_degree': 211, 'wind_dir': 'SSW', 'pressure': 1005, 'precip': 0.3, 'humidity': 42, 'cloudcover': 0, 'feelslike': 49, 'uv_index': 4, 'visibility': 10, 'is_day': 'yes'}}

# psycopg2 : Python external lib to connect to PostgreSQL
def connect_to_db():
  print("Connecting to the PostgreSQL database...")
  try:
    conn = psycopg2.connect(
      # 用airflow执行DB连接和在venv执行连接的配置是不一样的，docker内部用hostname加内部端口访问
      host="postgres",
      port=5432,
      dbname="db",
      user="db_user",
      password="db_password")
    return conn
  except psycopg2.Error as e:
    print(f"Database connection failed: {e}")
    raise

# connect_to_db()

def create_table(conn):
  print("Creating table if not exist...")
  try:
    cursor = conn.cursor()
    cursor.execute("""
        create schema if not exists raw;
        create table if not exists raw.weather_data (
                   id SERIAL PRIMARY KEY,
                   city TEXT,
                   temperature FLOAT,
                   weather_description TEXT,
                   wind_speed FLOAT,
                   time TIMESTAMP,
                   inserted_at TIMESTAMP DEFAULT NOW(),
                   utc_offset TEXT
                   );
    """)
    conn.commit() # connection object has a method of commit
    print("Table was created.")
  except psycopg2.Error as e:
    print(f"Failed to create table: {e}")
    raise

def insert_records(conn, data):
  print("Inserting weather data into the database...")
  try:
    weather = data['current']
    location = data['location']
    cursor = conn.cursor()
    cursor.execute("""
        insert into raw.weather_data (city, temperature, weather_description, wind_speed, time, inserted_at, utc_offset)
        values (%s, %s, %s, %s, %s, NOW(), %s);
    """, (
      location['name'],
      weather['temperature'],
      weather['weather_descriptions'][0],
      weather['wind_speed'],
      location['localtime'],
      location['utc_offset']
    ))
    conn.commit()
    print("Weather data inserted successfully.")
  except psycopg2.Error as e:
    print(f"Failed to insert records: {e}")
    raise

def main():
  try:
    # data = mock_fecth_data()  # Replace with fetch_data() for live data
    data = fetch_data()  # Uncomment this line to use live data from the API
    conn = connect_to_db()
    create_table(conn)
    insert_records(conn, data)
  except Exception as e:
    print(f"An error occurred during execution: {e}")
  finally:
    if conn:
      conn.close()
      print("Database connection closed.")

default_args = {
    'owner': 'mike',
    'description' : 'A DAG to orchestrate data',
    'start_date': datetime(2025, 7, 2, 11, 30),
    'catchup' : False,
}

dag = DAG('weather-api-postgres',
         default_args=default_args,
         schedule=timedelta(hours=12),
         catchup=False,
         tags=['weatherstack', 'postgres']
         )

with dag:
    task1 = PythonOperator(
        task_id='weather_data_ingestion',
        python_callable=main
    )
    #task2
