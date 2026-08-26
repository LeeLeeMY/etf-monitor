import os
import requests
import akshare as ak

# ---------- 配置区 ----------
# 这里填你的飞书 webhook（从环境变量读取）
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

# 报警阈值：溢价率低于该值（%）就报警（负值表示折价）
THRESHOLD = 9   # 例如 5 表示低于 5% 就报警（包括负值）
# -------------------------

# 定义要监控的 ETF 列表（按你要求分类，但代码里统一处理）
NAS_ETF = ["159501", "159941", "513100", "513300", "513110", "159696", "513870"]
SP_ETF  = ["513650", "513500", "159655", "159612"]
TARGET_CODES = NAS_ETF + SP_ETF

def send_msg(text):
    """发送消息到飞书"""
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
    """将原始溢价率数据转换成浮点数（单位：%）"""
    if isinstance(raw, str):
        # 字符串如 "-0.05%" 或 "0.05%"
        return float(raw.replace('%', ''))
    else:
        # 数字，可能是小数（-0.05）或已经百分数（-5）
        if abs(raw) < 1:
            return raw * 100
        else:
            return -raw

print("开始获取ETF数据...")
try:
    # 一次性获取所有ETF的实时行情
    df = ak.fund_etf_spot_em()
    print("数据获取成功，共 %d 只ETF" % len(df))

    # 过滤出我们关心的代码
    matched = df[df['代码'].isin(TARGET_CODES)]
    
    if matched.empty:
        print("未找到任何目标ETF，可能非交易时间无行情")
    else:
        alert_list = []   # 收集需要报警的ETF信息
        for idx, row in matched.iterrows():
            code = row['代码']
            name = row['名称']
            raw_premium = row['基金折价率']
            premium = parse_premium(raw_premium)
            print(f"{code} {name} 溢价率: {premium}%")

            # 判断是否低于阈值
            if premium < THRESHOLD:   # 注意：负数也满足小于正数
                alert_list.append(f"{code} {name} 溢价率为 {premium}%，低于 {THRESHOLD}%")
        
        # 统一发送报警（如果列表不为空）
        if alert_list:
            msg = "⚠️ ETF溢价监控报警：\n" + "\n".join(alert_list)
            send_msg(msg)
        else:
            print("所有ETF溢价率正常，未触发报警")

except Exception as e:
    error_msg = f"监控脚本运行异常: {e}"
    print(error_msg)
    send_msg(error_msg)
