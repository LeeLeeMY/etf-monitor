import os
import requests
import akshare as ak

WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

def send_msg(text):
    if WEBHOOK:
        try:
            requests.post(WEBHOOK, json={"msg_type":"text","content":{"text":text}})
            print("消息发送成功")
        except:
            print("消息发送失败")

print("开始获取ETF数据...")
try:
    df = ak.fund_etf_spot_em()
    row = df[df['代码'] == '513500']
    if not row.empty:
        premium_str = row['基金折价率'].iloc[0]
        premium = float(premium_str.replace('%', ''))
        print(f"当前513500溢价率: {premium}%")
        if premium <= -5:
            send_msg(f"⚠️ 标普500ETF(513500) 溢价率为 {premium}%，低于-5%，触发警报！")
        else:
            print("未触发报警（溢价率高于-5%）")
    else:
        print("未找到513500数据，可能非交易时间无行情")
except Exception as e:
    print(f"运行出错: {e}")
    send_msg(f"监控脚本运行异常，请检查: {e}")
