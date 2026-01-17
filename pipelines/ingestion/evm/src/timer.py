from contextlib import contextmanager
from datetime import datetime
import time

@contextmanager
def timer(name="BLOCK"):
    start_wall = datetime.now()
    start_perf = time.perf_counter()
    print(f"[{name} START] {start_wall:%Y-%m-%d %H:%M:%S}")
    try:
        yield
    finally:
        end_wall = datetime.now()
        end_perf = time.perf_counter()
        print(f"[{name} END]   {end_wall:%Y-%m-%d %H:%M:%S}")
        print(f"[{name} COST]  {end_perf - start_perf:.3f}s")

# how to use:
# with timer("spark_write_stream"):
#     query = df.writeStream.start()
#     query.awaitTermination(10)
