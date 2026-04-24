import requests
from bs4 import BeautifulSoup
import datetime
import os
import sys

PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")

GOODS_LIST = [
    {
        "name": "RIIZE",
        "url": "https://cn.ktown4u.com/iteminfo?goods_no=158460",
        "status_file": "status/status_158460.txt"
    },
    {
        "name": "NCT WISH",
        "url": "https://cn.ktown4u.com/iteminfo?goods_no=157626",
        "status_file": "status/status_157626.txt"
    }
]

def get_stock_status(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        page_text = soup.get_text()

        if "售罄" in page_text:
            return "SOLD_OUT"
        else:
            if "加入购物车" in page_text or "立即购买" in page_text:
                return "IN_STOCK"
            else:
                return "POSSIBLY_IN_STOCK"
    except Exception as e:
        print(f"[{datetime.datetime.now()}] 网络错误: {e}")
        return None

def send_wechat_push(title, message):
    if not PUSHPLUS_TOKEN:
        print("⚠️ PUSHPLUS_TOKEN 未设置，跳过微信推送")
        return
    api = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": message,
        "template": "html"
    }
    try:
        r = requests.post(api, json=data, timeout=10)
        print(f"微信推送结果: {r.json()}")
    except Exception as e:
        print(f"微信推送失败: {e}")

def load_last_status(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def save_status(filepath, status):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(status)

def main():
    print(f"开始检查 {len(GOODS_LIST)} 个商品...")
    any_state_changed = False

    for goods in GOODS_LIST:
        name = goods["name"]
        url = goods["url"]
        file = goods["status_file"]
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status = get_stock_status(url)
        if status is None:
            print(f"[{now}] {name} 网络错误，跳过")
            continue

        last_status = load_last_status(file)

        # 只要不是售罄，且状态与上次不同，就通知并标记变化
        if status != "SOLD_OUT" and status != last_status:
            msg = f"🎉 <b>【{name}】可能已补货！</b><br>检测状态：{status}<br><br>🔗 <a href='{url}'>点此直接购买</a><br>⏰ 时间：{now}"
            send_wechat_push(f"Ktown4u 补货提醒 - {name}", msg)
            save_status(file, status)
            any_state_changed = True
        elif status == "SOLD_OUT" and last_status != "SOLD_OUT" and last_status is not None:
            print(f"[{now}] {name} 再次售罄，更新记录")
            save_status(file, status)
            any_state_changed = True
        else:
            print(f"[{now}] {name} 状态无变化: {status}")

    if any_state_changed:
        sys.exit(1)  # 触发后续自动提交状态文件

if __name__ == "__main__":
    main()
