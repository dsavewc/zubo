import os
import base64
import requests
import time
import warnings
warnings.filterwarnings("ignore")

# 配置
API_KEY = os.getenv("DAYDAYMAP_KEY")
API_URL = "https://www.daydaymap.com/api/v1/raymap/search/asset/query"
# 原始搜索语句
raw_query = 'ip.province="湖南省" && header="udpxy"'
# 转base64编码keyword
keyword_b64 = base64.b64encode(raw_query.encode("utf-8")).decode("utf-8")
PAGE_SIZE = 100
OUTPUT_FILE = "ip.txt"
REQ_DELAY = 0.8

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

def fetch_all_udpxy():
    if not API_KEY:
        print("错误：未读取环境变量 DAYDAYMAP_KEY，请检查Secrets配置！")
        return

    all_targets = []
    page = 1

    while True:
        # 按官方文档传参：keyword 而非 query
        post_data = {
            "keyword": keyword_b64,
            "page": page,
            "page_size": PAGE_SIZE,
            "fields": "ip,port"  # 只返回需要的字段，减少流量
        }

        try:
            resp = requests.post(
                url=API_URL,
                headers=HEADERS,
                json=post_data,
                verify=False,
                timeout=25
            )
            resp.raise_for_status()
            res = resp.json()
        except Exception as e:
            print(f"第 {page} 页请求失败：{str(e)}")
            break

        if res.get("code") != 200:
            print(f"接口返回异常，code:{res.get('code')} msg: {res.get('msg')}")
            break

        data = res.get("data", {})
        asset_list = data.get("list", [])
        total_count = data.get("total", 0)
        current_page_size = len(asset_list)

        print(f"第{page}页 | 本页{current_page_size}条 | 总计{total_count}条")

        if not asset_list:
            print("无更多数据，抓取完成")
            break

        for item in asset_list:
            ip_addr = item.get("ip")
            port = item.get("port")
            if ip_addr and port:
                line = f"{ip_addr}:{port}"
                all_targets.append(line)

        # 判断是否翻页
        if page * PAGE_SIZE >= total_count:
            break

        page += 1
        time.sleep(REQ_DELAY)

    # 有序去重保存
    unique_list = list(dict.fromkeys(all_targets))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(unique_list))

    print(f"\n抓取结束，有效去重后共 {len(unique_list)} 条，已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_all_udpxy()
