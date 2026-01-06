import os
import requests
import time
from typing import Tuple
from datetime import datetime, timedelta, timezone

BASE_URL = "https://api.etherscan.io/v2/api?chainid=1"
# ETHERSCAN_API_KEY = "Z7928H9SFJI8NA633HT1D31FPR2WX4MFWX"
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

