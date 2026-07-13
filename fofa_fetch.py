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

# 关闭requests SSL警告
warnings.filterwarnings("ignore")

# ====================== 配置区 ======================
API_KEY = os.getenv("DAYDAYMAP_KEY")
API_URL = "https://www.daydaymap.com/api/v1/raymap/search/all"

# 北京时间时区
bj_tz = ZoneInfo("Asia/Shanghai")
now = datetime.now(tz=bj_tz)
today = now.strftime("%Y-%m-%d")

# 只查询今天全国udpxy资产
raw_query = f'ip.country="CN" && header="udpxy" && time="{today}"'
keyword_b64 = base64.b64encode(raw_query.encode("utf-8")).decode("utf-8")

PAGE_SIZE = 100
OUTPUT_FILE = "ip.txt"
TMP_CACHE = "tmp_cache.txt"
REQ_DELAY = 0.8
MAX_RETRY = 2
IP_DIR = "ip"
RTP_DIR = "rtp"
ZUBO_FILE = "zubo.txt"
# ====================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "api-key": API_KEY,
    "Content-Type": "application/json"
}


def fetch_all_udpxy():
    """第一阶段：抓取全国udpxy，保存 ip:port|省份|原始isp"""
    if not API_KEY or len(API_KEY.strip()) == 0:
        print("❌ 错误：未读取环境变量 DAYDAYMAP_KEY，请检查仓库Secrets配置！")
        return False
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
            "fields": "ip,port,province,isp"
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
                    return False

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
            province = item.get("province", "未知省份")
            isp_raw = item.get("isp", "")
            if ip_addr and port and str(port).isdigit():
                all_targets.append(f"{ip_addr}:{port}|{province}|{isp_raw}")

        if page * PAGE_SIZE >= total_count:
            break

        page += 1
        time.sleep(REQ_DELAY)

    unique_lines = list(dict.fromkeys(all_targets))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(unique_lines))

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
    return len(unique_lines) > 0


def parse_isp_name(isp_raw: str) -> str:
    txt = isp_raw.lower()
    if any(k in txt for k in ["telecom", "ct", "中国电信"]):
        return "电信"
    elif any(k in txt for k in ["unicom", "cu", "中国联通"]):
        return "联通"
    elif any(k in txt for k in ["mobile", "cm", "中国移动"]):
        return "移动"
    return "未知"


def classify_province_isp():
    """第二阶段：按省份运营商分类写入ip文件夹，每行带http://"""
    if not os.path.exists(OUTPUT_FILE):
        print(f"\n❌ 未找到 {OUTPUT_FILE}，跳过分类")
        return

    if not os.path.exists(IP_DIR):
        os.makedirs(IP_DIR)

    file_group = {}

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print("\n⚠️ ip.txt 无有效地址，跳过分类")
        return

    print(f"\n🔎 第二阶段：按接口省份运营商分类，共 {len(lines)} 个地址")
    for idx, line in enumerate(lines, 1):
        parts = line.split("|")
        addr = parts[0]
        province = parts[1] if len(parts)>=2 else "未知省份"
        raw_isp = parts[2] if len(parts)>=3 else ""

        isp_cn = parse_isp_name(raw_isp)
        file_name = f"{province}{isp_cn}"

        if file_name not in file_group:
            file_group[file_name] = []
        file_group[file_name].append(f"http://{addr}")

        if idx % 20 == 0:
            print(f"进度：{idx}/{len(lines)}")

    total_stat = {}
    for name, addr_list in file_group.items():
        save_path = os.path.join(IP_DIR, f"{name}.txt")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(addr_list))
        total_stat[name] = len(addr_list)
        print(f"✅ {name}.txt 写入完成，共{len(addr_list)}条")

    print("\n==================== 第二阶段汇总 ====================")
    for name, cnt in total_stat.items():
        print(f"{name}：{cnt} 条")
    print(f"📁 所有分类文件存放于 ./{IP_DIR}/ 目录")


# 第三阶段 你提供的函数（修正打印文案+统一变量）
def second_stage():
    print("🔔 第三阶段触发：生成 zubo.txt")
    if not os.path.exists(IP_DIR):
        print("⚠️ ip 目录不存在，跳过第三阶段")
        return

    if not os.path.exists(RTP_DIR):
        print("⚠️ rtp 目录不存在，无法进行第三阶段组合，跳过")
        return

    combined_lines = []

    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue

        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)

        if not os.path.exists(rtp_path):
            continue

        try:
            with open(ip_path, encoding="utf-8") as f1, open(rtp_path, encoding="utf-8") as f2:
                ip_lines = [x.strip() for x in f1 if x.strip()]
                rtp_lines = [x.strip() for x in f2 if x.strip()]
        except Exception as e:
            print(f"⚠️ 文件读取失败 {ip_file}：{e}")
            continue

        if not ip_lines or not rtp_lines:
            continue

        for ip_full in ip_lines:
            # ip_full 格式 http://1.1.1.1:80 ，去掉http://
            ip_port = ip_full.replace("http://", "")
            for rtp_line in rtp_lines:
                if "," not in rtp_line:
                    continue
                ch_name, rtp_url = rtp_line.split(",", 1)

                if "rtp://" in rtp_url:
                    part = rtp_url.split("rtp://", 1)[1]
                    combined_lines.append(f"{ch_name},http://{ip_port}/rtp/{part}")
                elif "udp://" in rtp_url:
                    part = rtp_url.split("udp://", 1)[1]
                    combined_lines.append(f"{ch_name},http://{ip_port}/udp/{part}")

    # 按完整url去重
    unique = {}
    for line in combined_lines:
        url_part = line.split(",", 1)[1]
        if url_part not in unique:
            unique[url_part] = line

    try:
        with open(ZUBO_FILE, "w", encoding="utf-8") as f:
            for line in unique.values():
                f.write(line + "\n")
        print(f"🎯 第三阶段完成，写入 {len(unique)} 条记录至 {ZUBO_FILE}")
    except Exception as e:
        print(f"❌ 写入 {ZUBO_FILE} 失败：{e}")


if __name__ == "__main__":
    # 第一阶段抓取
    has_data = fetch_all_udpxy()
    if has_data:
        # 第二阶段分类ip文件夹
        classify_province_isp()
        # 第三阶段组合rtp生成zubo.txt
        second_stage()
