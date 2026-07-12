import os
import re
import requests
import time
import concurrent.futures
import subprocess
from datetime import datetime, timezone, timedelta

# ===============================
# 配置区
FOFA_URLS = {
    "https://www.daydaymap.com/api/v1/raymap/search/asset/query": "ip.txt",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "api-key": "852b6c8f42a947c59086d5dbb5f8a831"
}
data = {
  "query": 'ip.province="湖南省" && header="udpxy"',
  "page": 1,
  "page_size": 10
}
r = requests.post('https://www.daydaymap.com/api/v1/raymap/search/all', headers=headers, json=data, verify=False, timeout=20)
json_data = r.requests.body
print(json_data)
    
