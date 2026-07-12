import os
import requests
import time
import warnings
warnings.filterwarnings("ignore")

# 配置项
API_KEY = os.getenv("DAYDAYMAP_KEY")
API_URL = "https://www.daydaymap.com/api/v1/raymap/search/asset/query"
SEARCH_QUERY = 'ip.province="湖南省" && header="udpxy"'
PAGE_SIZE = 100
OUTPUT_FILE = "ip.txt"
DELAY = 1  # 每页请求间隔，防止接口限流

# 请求头全局统一
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

def fetch_all_udpxy_ip():
    all_ips = []
    page = 1  # 起始页码
    
    while True:
        # 每页单独构造post参数
        post_data = {
            "query": SEARCH_QUERY,
            "page": page,
            "size": PAGE_SIZE
        }
        
        try:
            resp = requests.post(
                url=API_URL,
                headers=HEADERS,
                json=post_data,
                verify=False,
                timeout=20
            )
            resp.raise_for_status()  # 捕获4xx/5xx状态码
            res = resp.json()
        except Exception as e:
            print(f"第{page}页请求失败: {str(e)}")
            break
        
        data = res.get("data", {})
        asset_list = data.get("list", [])
        total = data.get("total", 0)
        print(f"正在抓取第{page}页，当前页数量：{len(asset_list)}，总量：{total}")
        
        # 提取ip字段，根据接口返回key自行调整（示例用ip_addr）
        if not asset_list:
            print("无更多数据，抓取结束")
            break
        
        for asset in asset_list:
            ip = asset.get("ip_addr")
            if ip:
                all_ips.append(ip)
        
        page += 1
        time.sleep(DELAY)
    
    # 去重并写入文件
    unique_ips = list(set(all_ips))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for ip in unique_ips:
            f.write(ip + "\n")
    print(f"抓取完成，共获取{len(unique_ips)}个独立IP，已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    if not API_KEY:
        print("错误：未读取到环境变量 DAYDAYMAP_KEY，请配置API密钥")
    else:
        fetch_all_udpxy_ip()
