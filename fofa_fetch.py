import os
import base64
import requests
import time
import warnings
from datetime import datetime
from zoneinfo import ZoneInfo
warnings.filterwarnings("ignore")

# ====================== 配置区 ======================
API_KEY = os.getenv("DAYDAYMAP_KEY")
API_URL = "https://www.daydaymap.com/api/v1/raymap/search/all"

# 强制东八区北京时间，消除服务器时区差
bj_tz = ZoneInfo("Asia/Shanghai")
today_str = datetime.now(tz=bj_tz).strftime("%Y-%m-%d")
# 检索语法拼接当日时间 YYYY-MM-DD
raw_query = f'ip.province="湖南省" && header="udpxy" && time={today_str}'
keyword_b64 = base64.b64encode(raw_query.encode("utf-8")).decode("utf-8")

PAGE_SIZE = 100
OUTPUT_FILE = "ip.txt"
TMP_CACHE = "tmp_cache.txt"
REQ_DELAY = 0.8
MAX_RETRY = 2
# ====================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "api-key": API_KEY,
    "Content-Type": "application/json"
}


def fetch_all_udpxy():
    if not API_KEY or len(API_KEY.strip()) == 0:
        print("❌ 错误：未读取环境变量 DAYDAYMAP_KEY，请检查仓库Secrets配置！")
        return
    print(f"✅ 密钥加载成功，密钥长度：{len(API_KEY)}")
    print(f"🌏 当前时区：Asia/Shanghai 北京时间")
    print(f"📅 筛选日期：{today_str}")
    print(f"🔍 检索语句：{raw_query}")
    print(f"📦 Base64检索关键词：{keyword_b64[:50]}...")

    all_targets = []
    page = 1

    while True:
        post_data = {
            "keyword": keyword_b64,
            "page": page,
            "page_size": PAGE_SIZE,
            "fields": "ip,port"
        }

        resp = None
        retry_times = 0
        success = False

        while retry_times < MAX_RETRY and not success:
            try:
                resp = requests.post(
                    url=API_URL,
                    headers=HEADERS,
                    json=post_data,
                    verify=False,
                    timeout=25
                )
                res = resp.json()
                success = True
            except Exception as e:
                retry_times += 1
                print(f"⚠️ 第{page}页第{retry_times}次请求异常: {str(e)}")
                time.sleep(1)
                if retry_times >= MAX_RETRY:
                    print(f"❌ 第{page}页重试耗尽，终止抓取")
                    with open(TMP_CACHE, "w", encoding="utf-8") as f:
                        f.write("\n".join(list(dict.fromkeys(all_targets))))
                    print(f"💾 已缓存当前数据至 {TMP_CACHE}")
                    return

        code = res.get("code", -1)
        msg = res.get("msg", "无返回信息")
        print(f"\n📄 第{page}页 | 接口返回信息：{msg} | code: {code}")

        if code != 200:
            print(f"❌ 接口调用失败，终止抓取 code:{code} msg:{msg}")
            with open(TMP_CACHE, "w", encoding="utf-8") as f:
                f.write("\n".join(list(dict.fromkeys(all_targets))))
            print(f"💾 已缓存当前数据至 {TMP_CACHE}")
            break

        data = res.get("data", {})
        asset_list = data.get("list", [])
        total_count = data.get("total", 0)
        current_page_size = len(asset_list)

        print(f"📊 第{page}页 | 本页{current_page_size}条 | 资产总量{total_count}条")

        if not asset_list:
            print("✅ 无更多资产，抓取结束")
            break

        for item in asset_list:
            ip_addr = item.get("ip")
            port = item.get("port")
            if ip_addr and port and str(port).isdigit():
                all_targets.append(f"{ip_addr}:{port}")

        if page * PAGE_SIZE >= total_count:
            break

        page += 1
        time.sleep(REQ_DELAY)

    unique_lines = list(dict.fromkeys(all_targets))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(unique_lines))

    if os.path.exists(TMP_CACHE):
        os.remove(TMP_CACHE)

    print(f"\n🎉 抓取完成！")
    print(f"📌 原始抓取总量：{len(all_targets)}")
    print(f"📌 去重后有效地址：{len(unique_lines)}")
    print(f"💾 结果保存至 {OUTPUT_FILE}")


def push_all_files():
    print("\n🚀 开始推送更新文件到 GitHub...")
    try:
        os.system('git config --global user.name "github-actions"')
        os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    except Exception:
        print("ℹ️ Git用户配置已存在，跳过")

    os.system("git add ip.txt")
    commit_ret = os.system('git commit -m "Auto update udpxy ip list [Date:{}]"'.format(today_str))
    if commit_ret != 0:
        print("ℹ️ 本次无IP更新，无需提交推送")
        return

    push_ret = os.system("git push origin main")
    if push_ret == 0:
        print("✅ 文件推送成功！")
    else:
        print("⚠️ Git推送失败，可能存在冲突或权限问题")


if __name__ == "__main__":
    fetch_all_udpxy()
    push_all_files()
