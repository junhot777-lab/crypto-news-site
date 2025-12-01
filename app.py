import datetime
import time

import requests
import feedparser
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# ✅ 한국 경제 뉴스 RSS
NEWS_FEEDS = [
    {
        "name": "조선일보 경제",
        "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/economy/?outputType=xml",  # 조선 경제 RSS :contentReference[oaicite:0]{index=0}
        "source": "조선일보",
    },
    {
        "name": "동아일보 경제",
        "url": "https://rss.donga.com/economy.xml",  # 동아 경제 RSS :contentReference[oaicite:1]{index=1}
        "source": "동아일보",
    },
    {
        "name": "중앙일보 경제",
        "url": "http://rss.joins.com/joins_money_list.xml",  # 중앙 머니(경제) RSS :contentReference[oaicite:2]{index=2}
        "source": "중앙일보",
    },
]


def fetch_news(limit=80):
    """여러 RSS에서 기사 모아서 최신순 정렬."""
    items = []

    for feed_info in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
        except Exception as e:
            print(f"[RSS ERROR] {feed_info['name']}: {e}")
            continue

        for entry in feed.entries[:40]:
            published = None
            published_ts = None

            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_ts = time.mktime(entry.published_parsed)
                published = datetime.datetime.fromtimestamp(
                    published_ts
                ).strftime("%Y-%m-%d %H:%M")
            else:
                published = getattr(entry, "published", "") or ""

            items.append(
                {
                    "title": entry.title,
                    "link": entry.link,
                    "summary": getattr(entry, "summary", "")[:200],
                    "source": feed_info["source"],
                    "published": published,
                    "published_ts": published_ts or 0,
                }
            )

    items.sort(key=lambda x: x["published_ts"], reverse=True)
    return items[:limit]


@app.route("/")
def index():
    news = fetch_news(limit=100)
    return render_template("index.html", news_list=news)


@app.route("/api/prices")
def api_prices():
    """
    업비트 현재가: KRW-BTC, KRW-ETH
    GET https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH :contentReference[oaicite:3]{index=3}
    + 환율: USD/KRW (기본적인 무료 공개 API 사용)
    """
    # 1) 업비트 시세
    upbit_url = "https://api.upbit.com/v1/ticker"
    upbit_params = {"markets": "KRW-BTC,KRW-ETH"}

    prices = {
        "BTC_KRW": None,
        "ETH_KRW": None,
        "USDKRW": None,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        resp = requests.get(upbit_url, params=upbit_params, timeout=3)
        resp.raise_for_status()
        data = resp.json()
        for item in data:
            market = item.get("market")
            trade_price = item.get("trade_price")
            if market == "KRW-BTC":
                prices["BTC_KRW"] = trade_price
            elif market == "KRW-ETH":
                prices["ETH_KRW"] = trade_price
    except Exception as e:
        print("[UPBIT ERROR]", e)

    # 2) 환율 USD/KRW (무료 공개 API: api.manana.kr) :contentReference[oaicite:4]{index=4}
    try:
        fx_url = "https://api.manana.kr/exchange/rate/KRW,USD.json"
        fx_resp = requests.get(fx_url, timeout=3)
        fx_resp.raise_for_status()
        fx_data = fx_resp.json()
        # 응답 구조 예: [{"name":"미국 USD","rate":1310.5,"date":"2025-11-30",...}, ...]
        for item in fx_data:
            if item.get("name", "").startswith("미국") or item.get("code") == "USD":
                # KRW 기준 USD 환율
                prices["USDKRW"] = item.get("rate")
                break
    except Exception as e:
        print("[FX ERROR]", e)

    return jsonify(prices)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
