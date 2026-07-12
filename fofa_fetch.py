import os
import base64
import requests
import time
import warnings
warnings.filterwarnings("ignore")

# 配置
API_KEY = os.getenv("DAYDAYMAP_KEY")
API_URL = "https://www.daydaymap.com/api/v1/raymap/search/all"
# 原始检索语句
raw_query = 'ip.province="湖南省" && header="udpxy"'
# 转为base64 keyword
keyword_b64 = base64.b64encode(raw_query.encode("utf-8")).decode("utf-8")
PAGE_SIZE = 100
OUTPUT_FILE = "ip.txt"
REQ_DELAY = 0.8

# 鉴权头：api-key 匹配官方示例
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

def fetch_all_udpxy():
    if not API_KEY:
        print("错误：未读取环境变量 DAYDAYMAP_KEY，请检查Secrets配置！")
        return
    print(f"密钥加载成功，长度：{len(API_KEY)}")

    all_targets = []
    page = 1

    while True:
        post_data = {
            "keyword": keyword_b64,
            "page": page,
            "page_size": PAGE_SIZE,
            "fields": "ip,port"
        }

        try:
            resp = requests.post(
                url=API_URL,
                headers=HEADERS,
                json=post_data,
                verify=False,
                timeout=25
            )
            res = resp.json()
            print(f"第{page}页返回：{res.get('msg')}")
        except Exception as e:
            print(f"第 {page} 页请求异常：{str(e)}")
            break

        if res.get("code") != 200:
            print(f"接口错误 code:{res.get('code')} msg:{res.get('msg')}")
            break

        data = res.get("data", {})
        asset_list = data.get("list", [])
        total_count = data.get("total", 0)
        current_page_size = len(asset_list)

        print(f"第{page}页 | 本页{current_page_size}条 | 总计{total_count}条")

        if not asset_list:
            print("无更多资产，抓取结束")
            break

        for item in asset_list:
            ip_addr = item.get("ip")
            port = item.get("port")
            if ip_addr and port:
                all_targets.append(f"{ip_addr}:{port}")

        # 判断是否到最后一页
        if page * PAGE_SIZE >= total_count:
            break

        page += 1
        time.sleep(REQ_DELAY)

    # 有序去重写入文件
    unique_lines = list(dict.fromkeys(all_targets))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(unique_lines))

    print(f"\n完成！共抓取 {len(unique_lines)} 条去重后的 udpxy 地址，保存至 {OUTPUT_FILE}")
    
def push_all_files():
    print("🚀 推送所有更新文件到 GitHub...")
    try:
        os.system('git config --global user.name "github-actions"')
        os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    except Exception:
        pass
    os.system("git add ip.txt || true")
    os.system("git push origin main || echo '⚠️ 推送失败'")



if __name__ == "__main__":
    fetch_all_udpxy()
