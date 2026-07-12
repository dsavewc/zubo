import os
import requests
import time
import warnings
warnings.filterwarnings("ignore")

# 配置
API_KEY = os.getenv("DAYDAYMAP_KEY")
API_URL = "https://www.daydaymap.com/api/v1/raymap/search/asset/query"
SEARCH_QUERY = 'ip.province="湖南省" && header="udpxy"'
PAGE_SIZE = 100
OUTPUT = "ip.txt"

# 全局headers，全程可用
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "apikey": API_KEY,
    "Content-Type": "application/json"
}
post_data = {
            "query": SEARCH_QUERY,
            "page": page,
            "size": PAGE_SIZE
        }

def fetch_assets():
    all_ips = []
    resp = requests.post(
            url=API\_URL,
            headers=HEADERS,
            json=post\_data,
            verify=False,
            timeout=20
        )
    res = resp.json()
    data = res.get("data", {})
    print(data)

