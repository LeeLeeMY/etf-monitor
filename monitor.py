import os
import requests
import akshare as ak

WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

def send_msg(text):
    if WEBHOOK:
        try:
            requests.post(WEBHOOK, json={"msg_type":"text","content":{"text":text}})
            print("消息发送成功")
        except Exception as e:
            print("消息发送失败:", e)

print("开始获取ETF数据...")
try:
    df = ak.fund_etf_spot_em()
    row = df[df['代码'] == '513500']
    if not row.empty:
        raw = row['基金折价率'].iloc[0]
        print(f"原始数据: {raw}（类型: {type(raw)}）")  # 这行会打印到日志，方便排查

        # ---------- 兼容处理 ----------
        if isinstance(raw, str):
            # 如果是字符串，去掉百分号并转为数字
            premium = float(raw.replace('%', ''))
        else:
            # 如果是数字（numpy.float64 或 float）
            # 判断：如果绝对值小于1，说明是小数形式（如 -0.05），需要乘以100
            if abs(raw) < 1:
                premium = raw * 100
            else:
                premium = raw   # 已经是百分比数字（如 -5）

        print(f"转换后溢价率: {premium}%")

        # 比较阈值（-5%）
        if premium <= -5:
            msg = f"⚠️ 标普500ETF(513500) 溢价率为 {premium}%，低于 -5%，触发警报！"
            send_msg(msg)
        else:
            print("未触发报警（溢价率高于 -5%）")
    else:
        print("未找到513500数据，可能非交易时间无行情")
except Exception as e:
    error_msg = f"监控脚本运行异常: {e}"
    print(error_msg)
    send_msg(error_msg)
