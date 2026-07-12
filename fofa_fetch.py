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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    "api-key": "aXAucHJvdmluY2U9Iua5luWNl+ecgSIgJiYgaGVhZGVyPSJ1ZHB4eSI="
}
data = {
  "query": 'ip.province="湖南省" && header="udpxy"'
  "page": 1,
  "page_size": 10
}

response = requests.post('https://www.daydaymap.com/api/v1/raymap/search/all', headers=headers, json=data, verify=False)
    
    
