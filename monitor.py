import requests
from bs4 import BeautifulSoup
import datetime
import os
import sys
import time

# 从 GitHub Secrets 读取 WxPusher 凭证
APP_TOKEN = os.environ.get("WXPUSHER_APP_TOKEN", "")
MY_UID = os.environ.get("WXPUSHER_UID", "")

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

def get_stock_status(url, retries=2):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            page_text = soup.get_text()
            if "售罄" in page_text:
                return "SOLD_OUT"
            elif "加入购物车" in page_text or "立即购买" in page_text:
                return "IN_STOCK"
            else:
                return "POSSIBLY_IN_STOCK"
        except Exception as e:
            if attempt < retries:
                print(f"[{datetime.datetime.now()}] 请求失败，10秒后重试第{attempt+1}次... ({e})")
                time.sleep(10)
            else:
                print(f"[{datetime.datetime.now()}] 网络错误（已重试{retries}次）: {e}")
                return None

def send_wxpusher(title, content):
    if not APP_TOKEN or not MY_UID:
        print("⚠️ WxPusher 凭证未配置，跳过推送")
        return
    payload = {
        "appToken": APP_TOKEN,
        "content": content,
        "summary": title,
        "contentType": 1,
        "uids": [MY_UID]
    }
    try:
        r = requests.post("https://wxpusher.zjiecode.com/api/send/message", json=payload, timeout=10)
        code = r.json().get("code")
        if code == 1000:
            print("✅ 微信通知已发送")
        else:
            print(f"❌ 通知失败: {r.json()}")
    except Exception as e:
        print(f"❌ 网络错误: {e}")

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
        if status != "SOLD_OUT" and status != last_status:
            content = f"【{name}】可能已补货！\n状态：{status}\n时间：{now}\n\n👉 点击购买：{url}"
            send_wxpusher(f"Ktown4u补货 - {name}", content)
            save_status(file, status)
            any_state_changed = True
        elif status == "SOLD_OUT" and last_status != "SOLD_OUT" and last_status is not None:
            print(f"[{now}] {name} 再次售罄")
            save_status(file, status)
            any_state_changed = True
        else:
            print(f"[{now}] {name} 状态无变化: {status}")
    if any_state_changed:
        sys.exit(1)

if __name__ == "__main__":
    main()
