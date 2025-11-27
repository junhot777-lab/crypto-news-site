import datetime
import time

import requests
import feedparser
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# ✅ RSS 뉴스 소스 (경제 카테고리)
NEWS_FEEDS = [
    {
        "name": "조선일보 경제",
        # 조선일보 경제 RSS :contentReference[oaicite:0]{index=0}
        "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/economy/?outputType=xml",
        "source": "조선일보",
    },
    {
        "name": "동아일보 경제",
        # 동아일보 경제 RSS :contentReference[oaicite:1]{index=1}
        "url": "https://rss.donga.com/economy.xml",
        "source": "동아일보",
    },
    # 여기다가 나중에 매일경제, 한경 등 더 추가 가능
]

def fetch_news(limit=50):
    """RSS 여러 개에서 기사 모아서 최신순으로 정렬."""
    items = []

    for feed_info in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
        except Exception as e:
            print(f"[RSS ERROR] {feed_info['name']}: {e}")
            continue

        for entry in feed.entries[:30]:
            # published 파싱
            published = None
            published_ts = None

            # feedparser가 제공하는 struct_time 사용
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

    # 최신순 정렬
    items.sort(key=lambda x: x["published_ts"], reverse=True)

    return items[:limit]


@app.route("/")
def index():
    news = fetch_news(limit=60)
    return render_template("index.html", news_list=news)


@app.route("/api/prices")
def api_prices():
    """
    업비트 현재가 REST API로 KRW-BTC, KRW-ETH 가격 가져오기.
    GET https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH :contentReference[oaicite:2]{index=2}
    """
    url = "https://api.upbit.com/v1/ticker"
    params = {"markets": "KRW-BTC,KRW-ETH"}

    try:
        resp = requests.get(url, params=params, timeout=3)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print("[UPBIT ERROR]", e)
        return jsonify({"error": "upbit_api_error"}), 500

    prices = {}
    for item in data:
        market = item.get("market")  # 예: 'KRW-BTC'
        trade_price = item.get("trade_price")  # 현재가
        if market == "KRW-BTC":
            prices["BTC_KRW"] = trade_price
        elif market == "KRW-ETH":
            prices["ETH_KRW"] = trade_price

    prices["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return jsonify(prices)


if __name__ == "__main__":
    # 로컬 테스트용
    app.run(host="0.0.0.0", port=5000, debug=True)
