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

def fetch_assets():
    all_ips = []
    page = 1
    while True:
        post_data = {
            "query": SEARCH_QUERY,
            "page": page,
            "size": PAGE_SIZE
        }
        resp = requests.post(
            url=API_URL,
            headers=HEADERS,
            json=post_data,
            verify=False,
            timeout=20
        )
        res = resp.json()
        data = res.get("data", {})
        list_data = data.get("list", [])
        if not list_data:
            break
        all_ips.extend(list_data)
        print(f"Page {page} done, total: {len(all_ips)}")
        page += 1
        time.sleep(1)
    return all_ips

def write_file(asset_list):
    with open(OUTPUT, "w", encoding="utf-8") as f:
        for item in asset_list:
            ip = item.get("ip")
            port = item.get("port")
            if ip and port:
                f.write(f"{ip}:{port}\n")
    print(f"Write {len(asset_list)} lines to {OUTPUT}")

if __name__ == "__main__":
    if not API_KEY:
        raise Exception("Missing DAYDAYMAP_KEY secret in repo")
    assets = fetch_assets()
    write_file(assets)
