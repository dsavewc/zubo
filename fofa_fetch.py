import os
import base64
import requests
import time
import warnings
import re
import subprocess
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed



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
IPTV_FILE = "IPTV.txt"
# ====================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

# ===============================
# 分类与映射配置
CHANNEL_CATEGORIES = {
    "央视频道": [
        "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
        "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17", "CCTV4K", "CCTV8K",
        "兵器科技", "风云音乐", "风云足球", "风云剧场", "怀旧剧场", "第一剧场", "女性时尚", "世界地理", "央视台球", "高尔夫网球",
        "央视文化精品", "卫生健康", "电视指南", "中学生", "发现之旅", "书法频道", "国学频道", "环球奇观"
    ],
    "卫视频道": [
        "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视", "广西卫视", "东南卫视", "海南卫视",
        "河北卫视", "河南卫视", "湖北卫视", "江西卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "天津卫视", "安徽卫视",
        "山东卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视", "甘肃卫视", "青海卫视",
        "新疆卫视", "西藏卫视", "三沙卫视", "兵团卫视", "延边卫视", "安多卫视", "康巴卫视", "农林卫视", "山东教育卫视",
        "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育"
    ],
    "数字频道": [
        "CHC动作电影", "CHC家庭影院", "CHC影迷电影", "淘电影", "淘精彩", "淘剧场", "淘4K", "淘娱乐", "淘BABY", "淘萌宠", "重温经典",
        "星空卫视", "ChannelV", "凤凰卫视中文台", "凤凰卫视资讯台", "凤凰卫视香港台", "凤凰卫视电影台", "求索纪录", "求索科学",
        "求索生活", "求索动物", "纪实人文", "金鹰纪实", "纪实科教", "睛彩青少", "睛彩竞技", "睛彩篮球", "睛彩广场舞", "魅力足球", "五星体育",
        "劲爆体育", "快乐垂钓", "茶频道", "先锋乒羽", "天元围棋", "汽摩", "梨园频道", "文物宝库", "武术世界", "哒啵赛事", "哒啵电竞", "黑莓电影", "黑莓动画",
        "乐游", "生活时尚", "都市剧场", "欢笑剧场", "游戏风云", "金色学堂", "动漫秀场", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通", "哈哈炫动", "嘉佳卡通",
        "中国交通", "中国天气", "华数4K", "华数星影", "华数动作影院", "华数喜剧影院", "华数家庭影院", "华数经典电影", "华数热播剧场", "华数碟战剧场",
        "华数军旅剧场", "华数城市剧场", "华数武侠剧场", "华数古装剧场", "华数魅力时尚", "华数少儿动画", "华数动画"
    ],
   "湖南节目": [
    "湖南都市", "湖南经视", "湖南爱晚", "湖南电影", "湖南电视剧", "湖南娱乐", "湖南教育", "湖南国际",
    "长沙综合", "长沙政法", "长沙嘉丽购", "长沙快乐购", "湘西文化旅游", "湘西综合", "张家界综合",
    "张家界公共", "衡阳综合", "衡阳文旅法治", "郴州综合", "芷江电视台", "永州新闻综合", "常德综合",
    "快乐购", "临武综合", "桂东融媒", "湖南九画面"
    ],
}

# ===== 映射（别名 -> 标准名） =====
CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经"],
    "CCTV3": ["CCTV-3", "CCTV-3 HD", "CCTV3 HD", "CCTV-3综艺"],
    "CCTV4": ["CCTV-4", "CCTV-4 HD", "CCTV4 HD", "CCTV-4中文国际"],
    "CCTV4欧洲": ["CCTV-4欧洲", "CCTV-4欧洲", "CCTV4欧洲 HD", "CCTV-4 欧洲", "CCTV-4中文国际欧洲", "CCTV4中文欧洲"],
    "CCTV4美洲": ["CCTV-4美洲", "CCTV-4北美", "CCTV4美洲 HD", "CCTV-4 美洲", "CCTV-4中文国际美洲", "CCTV4中文美洲"],
    "CCTV5": ["CCTV-5", "CCTV-5 HD", "CCTV5 HD", "CCTV-5体育"],
    "CCTV5+": ["CCTV-5+", "CCTV-5+ HD", "CCTV5+ HD", "CCTV-5+体育赛事"],
    "CCTV6": ["CCTV-6", "CCTV-6 HD", "CCTV6 HD", "CCTV-6电影"],
    "CCTV7": ["CCTV-7", "CCTV-7 HD", "CCTV7 HD", "CCTV-7国防军事"],
    "CCTV8": ["CCTV-8", "CCTV-8 HD", "CCTV8 HD", "CCTV-8电视剧"],
    "CCTV9": ["CCTV-9", "CCTV-9 HD", "CCTV9 HD", "CCTV-9纪录"],
    "CCTV10": ["CCTV-10", "CCTV-10 HD", "CCTV10 HD", "CCTV-10科教"],
    "CCTV11": ["CCTV-11", "CCTV-11 HD", "CCTV11 HD", "CCTV-11戏曲"],
    "CCTV12": ["CCTV-12", "CCTV-12 HD", "CCTV12 HD", "CCTV-12社会与法"],
    "CCTV13": ["CCTV-13", "CCTV-13 HD", "CCTV13 HD", "CCTV-13新闻"],
    "CCTV14": ["CCTV-14", "CCTV-14 HD", "CCTV14 HD", "CCTV-14少儿"],
    "CCTV15": ["CCTV-15", "CCTV-15 HD", "CCTV15 HD", "CCTV-15音乐"],
    "CCTV16": ["CCTV-16", "CCTV-16 HD", "CCTV-16 4K", "CCTV-16奥林匹克", "CCTV16 4K", "CCTV-16奥林匹克4K"],
    "CCTV17": ["CCTV-17", "CCTV-17 HD", "CCTV17 HD", "CCTV-17农业农村"],
    "CCTV4K": ["CCTV4K超高清", "CCTV-4K超高清", "CCTV-4K 超高清", "CCTV 4K"],
    "CCTV8K": ["CCTV8K超高清", "CCTV-8K超高清", "CCTV-8K 超高清", "CCTV 8K"],
    "兵器科技": ["CCTV-兵器科技", "CCTV兵器科技"],
    "风云音乐": ["CCTV-风云音乐", "CCTV风云音乐"],
    "第一剧场": ["CCTV-第一剧场", "CCTV第一剧场"],
    "风云足球": ["CCTV-风云足球", "CCTV风云足球"],
    "风云剧场": ["CCTV-风云剧场", "CCTV风云剧场"],
    "怀旧剧场": ["CCTV-怀旧剧场", "CCTV怀旧剧场"],
    "女性时尚": ["CCTV-女性时尚", "CCTV女性时尚"],
    "世界地理": ["CCTV-世界地理", "CCTV世界地理"],
    "央视台球": ["CCTV-央视台球", "CCTV央视台球"],
    "高尔夫网球": ["CCTV-高尔夫网球", "CCTV高尔夫网球", "CCTV央视高网", "CCTV-高尔夫·网球", "央视高网"],
    "央视文化精品": ["CCTV-央视文化精品", "CCTV央视文化精品", "CCTV文化精品", "CCTV-文化精品", "文化精品"],
    "卫生健康": ["CCTV-卫生健康", "CCTV卫生健康"],
    "电视指南": ["CCTV-电视指南", "CCTV电视指南"],
    "农林卫视": ["陕西农林卫视"],
    "三沙卫视": ["海南三沙卫视"],
    "兵团卫视": ["新疆兵团卫视"],
    "延边卫视": ["吉林延边卫视"],
    "安多卫视": ["青海安多卫视"],
    "康巴卫视": ["四川康巴卫视"],
    "山东教育卫视": ["山东教育"],
    "中国教育1台": ["CETV1", "中国教育一台", "中国教育1", "CETV-1 综合教育", "CETV-1"],
    "中国教育2台": ["CETV2", "中国教育二台", "中国教育2", "CETV-2 空中课堂", "CETV-2"],
    "中国教育3台": ["CETV3", "中国教育三台", "中国教育3", "CETV-3 教育服务", "CETV-3"],
    "中国教育4台": ["CETV4", "中国教育四台", "中国教育4", "CETV-4 职业教育", "CETV-4"],
    "早期教育": ["中国教育5台", "中国教育五台", "CETV早期教育", "华电早期教育", "CETV 早期教育"],
    "湖南卫视": ["湖南卫视4K"],
    "北京卫视": ["北京卫视4K"],
    "东方卫视": ["东方卫视4K"],
    "广东卫视": ["广东卫视4K"],
    "深圳卫视": ["深圳卫视4K"],
    "山东卫视": ["山东卫视4K"],
    "四川卫视": ["四川卫视4K"],
    "浙江卫视": ["浙江卫视4K"],
    "CHC影迷电影": ["CHC高清电影", "CHC-影迷电影", "影迷电影", "chc高清电影"],
    "淘电影": ["IPTV淘电影", "北京IPTV淘电影", "北京淘电影"],
    "淘精彩": ["IPTV淘精彩", "北京IPTV淘精彩", "北京淘精彩"],
    "淘剧场": ["IPTV淘剧场", "北京IPTV淘剧场", "北京淘剧场"],
    "淘4K": ["IPTV淘4K", "北京IPTV4K超清", "北京淘4K", "淘4K", "淘 4K"],
    "淘娱乐": ["IPTV淘娱乐", "北京IPTV淘娱乐", "北京淘娱乐"],
    "淘BABY": ["IPTV淘BABY", "北京IPTV淘BABY", "北京淘BABY", "IPTV淘baby", "北京IPTV淘baby", "北京淘baby"],
    "淘萌宠": ["IPTV淘萌宠", "北京IPTV萌宠TV", "北京淘萌宠"],
    "魅力足球": ["上海魅力足球"],
    "睛彩青少": ["睛彩羽毛球"],
    "求索纪录": ["求索记录", "求索纪录4K", "求索记录4K", "求索纪录 4K", "求索记录 4K"],
    "金鹰纪实": ["湖南金鹰纪实", "金鹰记实"],
    "纪实科教": ["北京纪实科教", "BRTV纪实科教", "纪实科教8K"],
    "星空卫视": ["星空衛視", "星空衛视", "星空卫視"],
    "ChannelV": ["CHANNEL-V", "Channel[V]"],
    "凤凰卫视中文台": ["凤凰中文", "凤凰中文台", "凤凰卫视中文", "凤凰卫视"],
    "凤凰卫视香港台": ["凤凰香港台", "凤凰卫视香港", "凤凰香港"],
    "凤凰卫视资讯台": ["凤凰资讯", "凤凰资讯台", "凤凰咨询", "凤凰咨询台", "凤凰卫视咨询台", "凤凰卫视资讯", "凤凰卫视咨询"],
    "凤凰卫视电影台": ["凤凰电影", "凤凰电影台", "凤凰卫视电影", "鳳凰衛視電影台", " 凤凰电影"],
    "茶频道": ["湖南茶频道"],
    "快乐垂钓": ["湖南快乐垂钓"],
    "先锋乒羽": ["湖南先锋乒羽"],
    "天元围棋": ["天元围棋频道"],
    "汽摩": ["重庆汽摩", "汽摩频道", "重庆汽摩频道"],
    "梨园频道": ["河南梨园频道", "梨园", "河南梨园"],
    "文物宝库": ["河南文物宝库"],
    "武术世界": ["河南武术世界"],
    "乐游": ["乐游频道", "上海乐游频道", "乐游纪实", "SiTV乐游频道", "SiTV 乐游频道"],
    "欢笑剧场": ["上海欢笑剧场4K", "欢笑剧场 4K", "欢笑剧场4K", "上海欢笑剧场"],
    "生活时尚": ["生活时尚4K", "SiTV生活时尚", "上海生活时尚"],
    "都市剧场": ["都市剧场4K", "SiTV都市剧场", "上海都市剧场"],
    "游戏风云": ["游戏风云4K", "SiTV游戏风云", "上海游戏风云"],
    "金色学堂": ["金色学堂4K", "SiTV金色学堂", "上海金色学堂"],
    "动漫秀场": ["动漫秀场4K", "SiTV动漫秀场", "上海动漫秀场"],
    "卡酷少儿": ["北京KAKU少儿", "BRTV卡酷少儿", "北京卡酷少儿", "卡酷动画"],
    "哈哈炫动": ["炫动卡通", "上海哈哈炫动"],
    "优漫卡通": ["江苏优漫卡通", "优漫漫画"],
    "金鹰卡通": ["湖南金鹰卡通"],
    "中国交通": ["中国交通频道"],
    "中国天气": ["中国天气频道"],
    "华数4K": ["华数低于4K", "华数4K电影", "华数爱上4K"],
    "湖南经视": ["湖南经砚"],
    "湖南爱晚": ["长沙爱晚", "爱晚"],
    "永州新闻综合": ["永州新闻综"],
}

# ====================== 第一阶段 抓取udpxy ======================
def fetch_all_udpxy():
    """抓取全国udpxy，保存 ip:port|省份|原始isp"""
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

# ====================== 第二阶段 省份运营商分类 ======================
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

# ====================== 第三阶段 拼接zubo.txt（线路携带 |运营商） ======================
def second_stage():
    print("🔔 第三阶段触发：生成 zubo.txt，格式：频道名,url|运营商")
    if not os.path.exists(IP_DIR):
        print(f"⚠️ 目录不存在：{IP_DIR}，跳过第三阶段")
        return
    print(f"✅ 检测到ip目录，目录内文件：{os.listdir(IP_DIR)}")

    if not os.path.exists(RTP_DIR):
        print(f"⚠️ 目录不存在：{RTP_DIR}，无法进行第三阶段组合，跳过")
        return
    print(f"✅ 检测到rtp目录，目录内文件：{os.listdir(RTP_DIR)}")

    combined_lines = []
    match_count = 0

    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue
        # 文件名直接作为运营商标识 例：湖南电信.txt → 湖南电信
        op_tag = ip_file.replace(".txt", "")
        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)

        if not os.path.exists(rtp_path):
            print(f"ℹ️ 无匹配rtp文件：{ip_file}，跳过")
            continue
        match_count += 1
        print(f"✅ 匹配成功：{ip_file} 运营商标识：{op_tag}")

        try:
            with open(ip_path, encoding="utf-8") as f1, open(rtp_path, encoding="utf-8") as f2:
                ip_lines = [x.strip() for x in f1 if x.strip()]
                rtp_lines = [x.strip() for x in f2 if x.strip()]
        except Exception as e:
            print(f"⚠️ 文件读取失败 {ip_file}：{e}")
            continue

        if not ip_lines or not rtp_lines:
            print(f"ℹ️ {ip_file} 地址/频道为空，跳过")
            continue

        for ip_full in ip_lines:
            ip_port = ip_full.replace("http://", "")
            for rtp_line in rtp_lines:
                if "," not in rtp_line:
                    continue
                ch_name, rtp_url = rtp_line.split(",", 1)
                full_url = ""
                if "rtp://" in rtp_url:
                    rtppart = rtp_url.split("rtp://", 1)[1]
                    full_url = f"http://{ip_port}/rtp/{rtppart}"
                elif "udp://" in rtp_url:
                    udppart = rtp_url.split("udp://", 1)[1]
                    full_url = f"http://{ip_port}/udp/{udppart}"
                # zubo格式：频道,url|运营商
                combined_lines.append(f"{ch_name},{full_url}|{op_tag}")

    print(f"📊 匹配文件总数：{match_count}，拼接总条数：{len(combined_lines)}")
    if len(combined_lines) == 0:
        print("❌ 无任何可拼接数据，不生成zubo.txt")
        return

    open(ZUBO_FILE, "a", encoding="utf-8").close()
    # 按url去重
    unique_dict = {}
    for line in combined_lines:
        front = line.split("|")[0]
        if front not in unique_dict:
            unique_dict[front] = line

    try:
        with open(ZUBO_FILE, "w", encoding="utf-8") as f:
            for line in unique_dict.values():
                f.write(line + "\n")
        print(f"🎯 zubo.txt 生成完成，共 {len(unique_dict)} 条")
        print("示例：CCTV1,http://58.35.123.183:3333/rtp/233.18.204.52:5140|中国联通")
    except Exception as e:
        print(f"❌ 写入 zubo.txt 失败：{e}")

# ====================== 第四阶段 多线程检测存活IP、生成IPTV.txt ======================
def third_stage():
    print("🧩 第四阶段：多线程检测存活IP、生成分类IPTV.txt")

    if not os.path.exists(ZUBO_FILE):
        print("⚠️ zubo.txt 不存在，跳过第四阶段")
        return

    def check_stream(url, timeout=5):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_streams", "-i", url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout + 2
            )
            return b"codec_type" in result.stdout
        except Exception:
            return False

    # 别名映射构建
    alias_map = {}
    for main_name, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            alias_map[alias] = main_name

    # 读取zubo.txt，拆分：频道,url|运营商
    groups = {}
    with open(ZUBO_FILE, encoding="utf-8") as f:
        for raw_line in f:
            raw_line = raw_line.strip()
            if "," not in raw_line or "|" not in raw_line:
                continue
            # 分割两部分：频道+url  / 运营商
            ch_url_part, op_name = raw_line.split("|", 1)
            ch_raw, url_full = ch_url_part.split(",", 1)
            # 频道标准化
            ch_std = alias_map.get(ch_raw, ch_raw)
            # 提取ip:port用于分组检测
            m = re.match(r"http://([^/]+)/", url_full)
            if not m:
                continue
            ip_port = m.group(1)
            # 存入：(标准频道名, 纯url, 运营商)
            groups.setdefault(ip_port, []).append((ch_std, url_full, op_name.strip()))

    # 多线程检测存活IP
    print(f"🚀 开始检测 {len(groups)} 组IP代理")
    playable_ips = set()

    # 检测函数移至线程池外，解决作用域报错
    def detect_ip(ip_port, entries):
        rep_urls = [url for c, url, op in entries if c == "CCTV1"]
        if not rep_urls and entries:
            rep_urls = [entries[0][1]]
        alive = any(check_stream(u) for u in rep_urls)
        return ip_port, alive

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(detect_ip, ip_port, ch_list): ip_port for ip_port, ch_list in groups.items()}
        for future in as_completed(futures):
            try:
                ip_ok, alive_flag = future.result()
                if alive_flag:
                    playable_ips.add(ip_ok)
            except Exception as e:
                print(f"⚠️ 线程检测异常: {e}")

    print(f"✅ 检测完成，可用代理IP：{len(playable_ips)} 个")

    # 收集有效线路，$后直接使用zubo中|后的运营商
    ch_total = {}
    operator_ip_map = {}
    for ip_port, ch_entries in groups.items():
        if ip_port not in playable_ips:
            continue
        for ch_std, url, op_name in ch_entries:
            # IPTV行格式：标准频道,url$运营商
            final_line = f"{ch_std},{url}${op_name}"
            if final_line not in ch_total.get(ch_std, set()):
                ch_total.setdefault(ch_std, set()).add(final_line)
                operator_ip_map.setdefault(op_name, set()).add(ip_port)

    # 刷新ip目录文件，只保留存活IP
    for op, ip_set in operator_ip_map.items():
        save_path = os.path.join(IP_DIR, f"{op}.txt")
        with open(save_path, "w", encoding="utf-8") as wf:
            for item in sorted(ip_set):
                wf.write(f"http://{item}\n")
        print(f"📁 更新 {op}.txt 共 {len(ip_set)} 个可用IP")

    # 生成分类 IPTV.txt
    beijing_now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    disclaimer_url = "http://kakaxi.indevs.in/LOGO/Disclaimer.mp4"
    with open(IPTV_FILE, "w", encoding="utf-8") as out_f:
        out_f.write(f"更新时间: {beijing_now}（北京时间）\n\n")
        out_f.write("更新时间,#genre#\n")
        out_f.write(f"{beijing_now},{disclaimer_url}\n\n")
        # 遍历全部大分类输出
        for group_title, ch_list in CHANNEL_CATEGORIES.items():
            out_f.write(f"{group_title},#genre#\n")
            for ch_name in ch_list:
                if ch_name in ch_total:
                    for line in sorted(ch_total[ch_name]):
                        out_f.write(line + "\n")
            out_f.write("\n")
    total_lines = sum(len(v) for v in ch_total.values())
    print(f"🎯 IPTV.txt 生成完毕，有效源总数：{total_lines}")
# ===============================
# 文件推送
def push_all_files():
    print("🚀 推送所有更新文件到 GitHub...")
    try:
        os.system('git config --global user.name "github-actions"')
        os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    except Exception:
        pass

    os.system("git add ip.txt || true")
    os.system("git add 计数.txt || true")
    os.system("git add ip/*.txt || true")
    os.system("git add IPTV.txt || true")
    os.system('git commit -m "自动更新：计数、IP文件、IPTV.txt" || echo "⚠️ 无需提交"')
    os.system("git push origin main || echo '⚠️ 推送失败'")


# ====================== 程序入口 ======================
if __name__ == "__main__":
    import traceback
    try:
        # 第一阶段 抓取全国udpxy
        has_data = fetch_all_udpxy()
        if has_data:
            # 第二阶段 按省份运营商分类
            classify_province_isp()
            # 第三阶段 匹配rtp文件生成zubo.txt
            second_stage()
            # 第四阶段 ffprobe多线程检测、刷新ip文件、输出分类IPTV.txt
            third_stage()
        else:
            print("ℹ️ 第一阶段未抓取到任何IP数据，终止后续流程")
    except Exception as e:
        print("\n❌ 程序运行发生致命异常：")
        print(traceback.format_exc())
        exit(1)
    print("\n✅ 全部流程执行完毕，无异常")
