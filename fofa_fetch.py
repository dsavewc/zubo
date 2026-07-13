import os
import base64
import requests
import time
import warnings
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

warnings.filterwarnings("ignore")

# ====================== 配置区 ======================
API_KEY = os.getenv("DAYDAYMAP_KEY")
API_URL = "https://www.daydaymap.com/api/v1/raymap/search/all"

# 北京时间时区
bj_tz = ZoneInfo("Asia/Shanghai")
now = datetime.now(tz=bj_tz)
today = now.strftime("%Y-%m-%d")

# 只查询今日数据
raw_query = f'ip.province="湖南省" && header="udpxy" && time="{today}"'
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
    print(f"📅 筛选日期：{today}")
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
                    unique_temp = list(dict.fromkeys(all_targets))
                    with open(TMP_CACHE, "w", encoding="utf-8") as f:
                        f.write("\n".join(unique_temp))
                    print(f"💾 已缓存当前数据至 {TMP_CACHE}")
                    return

        code = res.get("code", -1)
        msg = res.get("msg", "无返回信息")
        print(f"\n📄 第{page}页 | 接口返回信息：{msg} | code: {code}")

        if code != 200:
            print(f"❌ 接口调用失败，终止抓取 code:{code} msg:{msg}")
            unique_temp = list(dict.fromkeys(all_targets))
            with open(TMP_CACHE, "w", encoding="utf-8") as f:
                f.write("\n".join(unique_temp))
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

    # 计数文件标注今日筛选
    count_text = (
        f"抓取时间(北京时间)：{now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"筛选日期：{today}\n"
        f"有效udpxy地址总数：{len(unique_lines)}"
    )
    with open("计数.txt", "w", encoding="utf-8") as f:
        f.write(count_text)

    if os.path.exists(TMP_CACHE):
        os.remove(TMP_CACHE)

    print(f"\n🎉 抓取完成！")
    print(f"📌 原始抓取总量：{len(all_targets)}")
    print(f"📌 去重后有效地址：{len(unique_lines)}")
    print(f"💾 结果保存至 {OUTPUT_FILE}、计数.txt")

# ===============================
# 第二阶段 判断Ip.txt的Ip地址的运营商并在ip文件夹下保存

def get_isp_from_api(data):
    isp_raw = (data.get("isp") or "").lower()

    if "telecom" in isp_raw or "ct" in isp_raw or "chinatelecom" in isp_raw:
        return "电信"
    elif "unicom" in isp_raw or "cu" in isp_raw or "chinaunicom" in isp_raw:
        return "联通"
    elif "mobile" in isp_raw or "cm" in isp_raw or "chinamobile" in isp_raw:
        return "移动"

    return "未知"


def get_isp_by_regex(ip):
    if re.match(r"^(1[0-9]{2}|2[0-3]{2}|42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "电信"

    elif re.match(r"^(42|43|58|59|60|61|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|175|180|182|183|184|185|186|187|188|189|223)\.", ip):
        return "联通"

    elif re.match(r"^(223|36|37|38|39|100|101|102|103|104|105|106|107|108|109|134|135|136|137|138|139|150|151|152|157|158|159|170|178|182|183|184|187|188|189)\.", ip):
        return "移动"

    return "未知"

# ===============================
# 文件推送
def push_all_files():
    print("🚀 推送所有更新文件到 GitHub...")
    try:
        os.system('git config --global user.name "github-actions"')
        os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    except Exception:
        pass

    os.system("git add 计数.txt || true")
    os.system("git add ip/*.txt || true")
    os.system("git add IPTV.txt || true")
    os.system('git commit -m "自动更新：计数、IP文件、IPTV.txt" || echo "⚠️ 无需提交"')
    os.system("git push origin main || echo '⚠️ 推送失败'")


if __name__ == "__main__":
    # 确保目录存在
    os.makedirs(IP_DIR, exist_ok=True)
    os.makedirs(RTP_DIR, exist_ok=True)
    fetch_all_udpxy()
