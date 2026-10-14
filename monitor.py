import os
import requests
import re

WEBHOOK = os.environ.get("FEISHU_WEBHOOK")
THRESHOLD = 5  # 报警阈值

NAS_ETF = ["159501", "159941", "513100", "513300", "513110", "159696", "513870"]
SP_ETF  = ["513650", "513500", "159655", "159612"]
TARGET_CODES = NAS_ETF + SP_ETF

def send_msg(text):
    if WEBHOOK:
        try:
            resp = requests.post(WEBHOOK, json={"msg_type": "text", "content": {"text": text}}, timeout=10)
            if resp.status_code == 200:
                print("消息发送成功")
            else:
                print(f"消息发送失败，状态码：{resp.status_code}")
        except Exception as e:
            print("消息发送异常:", e)

def fetch_etf_quotes_tencent(codes):
    """
    通过腾讯财经 API 批量获取 ETF 实时行情
    接口返回格式（GBK 编码）：
    v_sh513100="1~纳指ETF~513100~1.234~..."
    """
    # 腾讯接口需要加市场前缀：5开头为沪市(sh)，1开头为深市(sz)
    symbols = []
    for code in codes:
        if code.startswith("5"):
            symbols.append(f"sh{code}")
        elif code.startswith("1"):
            symbols.append(f"sz{code}")
    
    url = f"http://qt.gtimg.cn/q={','.join(symbols)}"
    resp = requests.get(url, timeout=15)
    resp.encoding = "gbk"
    
    results = {}
    for line in resp.text.strip().split(";"):
        line = line.strip()
        if not line or "=" not in line:
            continue
        # 提取变量名中的代码，如 v_sh513100
        match = re.search(r'v_(sh|sz)(\d{6})="(.+)"', line)
        if not match:
            continue
        code = match.group(2)
        fields = match.group(3).split("~")
        # 腾讯返回字段说明（部分关键字段位置）：
        # fields[1] = 名称, fields[3] = 最新价, fields[4] = 昨收
        # fields[31] = IOPV(实时估值), fields[32] = 折溢价率(%)
        name = fields[1] if len(fields) > 1 else ""
        price = float(fields[3]) if len(fields) > 3 and fields[3] else 0
        iopv = float(fields[31]) if len(fields) > 31 and fields[31] else 0
        premium = float(fields[32]) if len(fields) > 32 and fields[32] else None
        
        results[code] = {
            "name": name,
            "price": price,
            "iopv": iopv,
            "premium": premium,  # 腾讯返回的溢价率，正值为溢价，负值为折价
        }
    return results

print("开始执行监控...")

try:
    quotes = fetch_etf_quotes_tencent(TARGET_CODES)
    print(f"数据获取成功，共 {len(quotes)} 只ETF")

    if not quotes:
        print("未获取到行情数据，可能非交易时间")
    else:
        alert_list = []
        for code, data in quotes.items():
            name = data["name"]
            premium = data["premium"]
            
            if premium is None:
                print(f"{code} {name} 溢价率数据缺失，跳过")
                continue
            
            print(f"{code} {name} 溢价率: {premium}%")
            
            # 腾讯返回的溢价率：正值=溢价，负值=折价
            if premium < THRESHOLD:
                alert_list.append(f"{code} {name} 溢价率为 {premium}%，低于 {THRESHOLD}%")

        if alert_list:
            msg = "⚠️ ETF溢价监控报警：\n" + "\n".join(alert_list)
            send_msg(msg)
        else:
            print("所有ETF溢价率正常，未触发报警")

except Exception as e:
    error_msg = f"监控脚本运行异常: {e}"
    print(error_msg)
    send_msg(error_msg)
