import os
import requests
import akshare as ak

# ---------- 配置 ----------
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")
THRESHOLD = 5   # 报警阈值：溢价率 < 9% 时报警（你自己调 ，想改就改这个数）
# -----------------------

NAS_ETF = ["159501", "159941", "513100", "513300", "513110", "159696", "513870"]
SP_ETF  = ["513650", "513500", "159655", "159612"]
TARGET_CODES = NAS_ETF + SP_ETF

def send_msg(text):
    if WEBHOOK:
        try:
            resp = requests.post(WEBHOOK, json={"msg_type":"text","content":{"text":text}})
            if resp.status_code == 200:
                print("消息发送成功")
            else:
                print(f"消息发送失败，状态码：{resp.status_code}")
        except Exception as e:
            print("消息发送异常:", e)

def parse_premium(raw):
    """将原始折价率转换为溢价率（取反）"""
    if isinstance(raw, str):
        val = float(raw.replace('%', ''))
    else:
        if abs(raw) < 1:
            val = raw * 100
        else:
            val = raw
    return -val

print("开始执行监控...")

try:
    df = ak.fund_etf_spot_em()
    print(f"数据获取成功，共 {len(df)} 只ETF")
    matched = df[df['代码'].isin(TARGET_CODES)]
    if matched.empty:
        print("未找到目标ETF，可能非交易时间无行情")
    else:
        alert_list = []
        for idx, row in matched.iterrows():
            code = row['代码']
            name = row['名称']
            raw = row['基金折价率']
            premium = parse_premium(raw)
            print(f"{code} {name} 溢价率: {premium}%")

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
