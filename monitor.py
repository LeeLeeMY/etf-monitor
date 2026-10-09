import os
import requests
import akshare as ak
import pandas as pd

# ---------- 配置 ----------
WEBHOOK = os.environ.get("FEISHU_WEBHOOK")
JSL_COOKIE = os.environ.get("JSL_COOKIE", "")  # 集思录登录 Cookie
THRESHOLD = 5   # 报警阈值：溢价率 < 5% 时报警（可根据需要调整）

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

print("开始执行监控...")

try:
    # 使用集思录 QDII 欧美指数接口，并传入 Cookie 以获取完整数据
    df = ak.qdii_e_index_jsl(cookie=JSL_COOKIE)
    print(f"数据获取成功，共 {len(df)} 条记录")
    
    # 筛选目标 ETF
    matched = df[df['代码'].isin(TARGET_CODES)]
    
    if matched.empty:
        print("未找到目标ETF，可能非交易时间、Cookie已过期或数据源未覆盖")
    else:
        alert_list = []
        for idx, row in matched.iterrows():
            code = row['代码']
            name = row['名称']
            premium_raw = row['T-1溢价率']
            
            # --- 处理 '-' 或空值的情况 ---
            if pd.isna(premium_raw) or str(premium_raw).strip() in ['-', '--', '']:
                print(f"{code} {name} 溢价率为 '{premium_raw}'，数据未更新或缺失，跳过")
                continue
            
            # --- 解析溢价率，增加异常捕获 ---
            try:
                if isinstance(premium_raw, str):
                    premium = float(premium_raw.replace('%', '').strip())
                else:
                    premium = float(premium_raw)
            except ValueError:
                print(f"{code} {name} 溢价率解析异常: {premium_raw}，跳过")
                continue
            # ------------------------------------
            
            print(f"{code} {name} 溢价率: {premium}%")

            # 判断是否触发报警
            if premium < THRESHOLD:
                alert_list.append(f"{code} {name} 溢价率为 {premium}%，低于 {THRESHOLD}%")
        
        # 发送飞书消息
        if alert_list:
            msg = "⚠️ ETF溢价监控报警：\n" + "\n".join(alert_list)
            send_msg(msg)
        else:
            print("所有ETF溢价率正常，未触发报警")

except Exception as e:
    error_msg = f"监控脚本运行异常: {e}"
    print(error_msg)
    send_msg(error_msg)
