import os
import base64
import requests
import time
import warnings
import re
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
# 运营商分类根文件夹
ROOT_DIR = "ip"
# IP地理运营商查询接口
ISP_API = "https://api.ip.sb/geoip/"
# ====================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "api-key": API_KEY,
    "Content-Type": "application/json"
}


def fetch_all_udpxy():
    """第一阶段：抓取湖南今日udpxy地址，仅返回ip+port"""
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
            if ip_addr and port and str(port).isdigit():
                all_targets.append(f"{ip_addr}:{port}")

        if page * PAGE_SIZE >= total_count:
            break

        page += 1
        time.sleep(REQ_DELAY)

    # 去重写入总文件
    unique_lines = list(dict.fromkeys(all_targets))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(unique_lines))

    # 计数文件
    count_text = (
        f"抓取时间(北京时间)：{now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"筛选日期：{today}\n"
        f"有效udpxy地址总数：{len(unique_lines)}"
    )
    with open("计数.txt", "w", encoding="utf-8") as f:
        f.write(count_text)

    # 删除临时缓存
    if os.path.exists(TMP_CACHE):
        os.remove(TMP_CACHE)

    print(f"\n🎉 抓取完成！")
    print(f"📌 原始抓取总量：{len(all_targets)}")
    print(f"📌 去重后有效地址：{len(unique_lines)}")
    print(f"💾 结果保存至 {OUTPUT_FILE}、计数.txt")
    return len(unique_lines) > 0


def get_ip_info(ip: str):
    """查询IP省份+运营商，返回 (省份中文名, 运营商)"""
    province = "未知省份"
    isp = None
    try:
        resp = requests.get(f"{ISP_API}{ip}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # 解析省份
            region_en = data.get("region", "")
            region_name = data.get("region_name", "")
            if "Hunan" in region_en or "湖南" in region_name:
                province = "湖南"
            elif "Guangdong" in region_en or "广东" in region_name:
                province = "广东"
            elif "Jiangsu" in region_en or "江苏" in region_name:
                province = "江苏"
            elif "Zhejiang" in region_en or "浙江" in region_name:
                province = "浙江"

            # 解析运营商
            isp_raw = (data.get("isp") or "").lower()
            org = (data.get("organization") or "").lower()
            full_text = isp_raw + org
            if any(k in full_text for k in ["telecom", "ct", "chinatelecom"]):
                isp = "电信"
            elif any(k in full_text for k in ["unicom", "cu", "chinaunicom"]):
                isp = "联通"
            elif any(k in full_text for k in ["mobile", "cm", "chinamobile"]):
                isp = "移动"
    except Exception:
        pass
    return province, isp


def get_isp_by_regex(ip: str) -> str:
    """IP网段正则兜底判断运营商"""
    ip_prefix = ip.split(".")[0]
    telecom_prefix = {"100","101","102","103","104","105","106","107","108","109",
                      "110","111","112","113","114","115","116","117","118","119",
                      "120","121","122","123","124","125","126","127","175","180",
                      "181","189","218","219","220","221","222"}
    unicom_prefix = {"36","37","38","39","42","43","58","59","60","61",
                     "110","111","112","113","114","115","116","117","118","119",
                     "120","121","122","123","124","125","126","127","175","186"}
    mobile_prefix = {"223","134","135","136","137","138","139","150","151","152",
                     "157","158","159","170","178","182","183","184","187","188"}

    if ip_prefix in telecom_prefix:
        return "电信"
    elif ip_prefix in unicom_prefix:
        return "联通"
    elif ip_prefix in mobile_prefix:
        return "移动"
    return "未知"


def classify_province_isp():
    """第二阶段：按 省份+运营商 生成独立txt文件"""
    if not os.path.exists(OUTPUT_FILE):
        print(f"\n❌ 未找到 {OUTPUT_FILE}，跳过分类")
        return

    # 创建根目录 ip
    if not os.path.exists(ROOT_DIR):
        os.makedirs(ROOT_DIR)

    # 存储结构 {"湖南电信": [], "湖南联通": [], "广东电信": [] ...}
    file_group = {}

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print("\n⚠️ ip.txt 无有效地址，跳过分类")
        return

    print(f"\n🔎 开始识别省份+运营商，共 {len(lines)} 个地址")
    for idx, line in enumerate(lines, 1):
        ip = line.split(":")[0]
        province, isp = get_ip_info(ip)
        # 接口获取运营商失败则网段兜底
        if not isp:
            isp = get_isp_by_regex(ip)

        # 拼接文件名标识：湖南电信、广东联通、未知省份未知
        file_tag = f"{province}{isp}"
        if file_tag not in file_group:
            file_group[file_tag] = []
        file_group[file_tag].append(line)

        # 打印进度
        if idx % 20 == 0:
            print(f"进度：{idx}/{len(lines)}")
        time.sleep(0.25)

    # 批量写入所有分组文件
    total_stat = {}
    for tag, addr_list in file_group.items():
        save_path = os.path.join(ROOT_DIR, f"{tag}.txt")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(addr_list))
        total_stat[tag] = len(addr_list)
        print(f"✅ {tag}.txt 写入完成，共{len(addr_list)}条")

    # 汇总输出
    print("\n==================== 全局汇总 ====================")
    for name, count in total_stat.items():
        print(f"{name}：{count} 条")
    print(f"📁 所有分类文件存放于 ./ip/ 目录")


if __name__ == "__main__":
    # 第一阶段抓取udpxy地址
    has_data = fetch_all_udpxy()
    # 有数据才执行省份运营商分类
    if has_data:
        classify_province_isp()
