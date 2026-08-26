import os
import requests
import akshare as ak
import datetime

# ---------- 配置 ----------
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")
THRESHOLD = 9   # 报警阈值：溢价率 < 5% 时报警
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

def is_trading_time(hour, minute):
    """判断是否在有效交易时段（9:30-11:30 和 13:00-15:00）"""
    if hour == 9 and minute >= 30:
        return True
    if hour == 10:
        return True
    if hour == 11 and minute < 30:
        return True
    if hour == 13:
        return True
    if hour == 14:
        return True
    if hour == 15 and minute == 0:
        return True
    return False

def is_high_freq(hour, minute):
    """高频时段：9:30-10:30 和 14:30-15:00"""
    if hour == 9 and minute >= 30:
        return True
    if hour == 10 and minute < 30:
        return True
    if hour == 14 and minute >= 30:
        return True
    if hour == 15 and minute == 0:
        return True
    return False

def is_low_freq(hour, minute):
    """低频时段：10:30-14:30"""
    if hour == 10 and minute >= 30:
        return True
    if hour in [11, 12, 13]:   # 包含午休，但会先被 is_trading_time 过滤掉 11:30-13:00
        return True
    if hour == 14 and minute < 30:
        return True
    return False

# ========== 主逻辑 ==========
print("开始执行监控...")

# 1. 获取当前北京时间
beijing_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
hour = beijing_now.hour
minute = beijing_now.minute
weekday = beijing_now.weekday()  # 0=周一, 6=周日

# 2. 周末跳过
if weekday >= 5:
    print("周末休市，跳过")
    exit(0)

# 3. 判断交易时段
if not is_trading_time(hour, minute):
    print("非交易时段（集合竞价/午休/收盘后），跳过")
    exit(0)

# 4. 判断高频/低频
if is_high_freq(hour, minute):
    print(f"高频时段（{hour:02d}:{minute:02d}），正常执行")
    pass   # 直接执行
elif is_low_freq(hour, minute):
    # 低频时段，只允许每15分钟执行一次（0,15,30,45分）
    if minute % 15 != 0:
        print(f"低频时段，分钟 {minute} 不是15的倍数，跳过")
        exit(0)
    else:
        print(f"低频时段，分钟 {minute} 是15的倍数，执行")
else:
    # 理论上不会到这里
    print("未知时段，跳过")
    exit(0)

# 5. 获取数据并报警
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
