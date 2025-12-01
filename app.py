import datetime
import time

import requests
import feedparser
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# 한국 경제 뉴스 RSS
NEWS_FEEDS = [
    {
        "name": "조선일보 경제",
        "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/economy/?outputType=xml",
        "source": "조선일보",
    },
    {
        "name": "동아일보 경제",
        "url": "https://rss.donga.com/economy.xml",
        "source": "동아일보",
    },
    {
        "name": "중앙일보 경제",
        "url": "http://rss.joins.com/joins_money_list.xml",
        "source": "중앙일보",
    },
]


def fetch_news(limit=80):
    items = []
    for feed_info in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
        except Exception as e:
            print(f"[RSS ERROR] {feed_info['name']}: {e}")
            continue

        for entry in feed.entries[:40]:
            published_ts = 0
            published = ""

            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_ts = time.mktime(entry.published_parsed)
                published = datetime.datetime.fromtimestamp(
                    published_ts
                ).strftime("%Y-%m-%d %H:%M")
            else:
                published = getattr(entry, "published", "")

            items.append(
                {
                    "title": entry.title,
                    "link": entry.link,
                    "summary": getattr(entry, "summary", "")[:200],
                    "source": feed_info["source"],
                    "published": published,
                    "published_ts": published_ts,
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
    upbit_url = "https://api.upbit.com/v1/ticker"
    upbit_params = {"markets": "KRW-BTC,KRW-ETH"}

    prices = {
        "BTC_KRW": None,
        "ETH_KRW": None,
        "USDKRW": None,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 업비트
    try:
        resp = requests.get(upbit_url, params=upbit_params, timeout=3)
        resp.raise_for_status()
        data = resp.json()
        for item in data:
            if item["market"] == "KRW-BTC":
                prices["BTC_KRW"] = item["trade_price"]
            elif item["market"] == "KRW-ETH":
                prices["ETH_KRW"] = item["trade_price"]
    except Exception as e:
        print("[UPBIT ERROR]", e)

    # USD/KRW 환율 (open.er-api)
    try:
        fx_url = "https://open.er-api.com/v6/latest/USD"
        fx_resp = requests.get(fx_url, timeout=5)
        fx_resp.raise_for_status()
        fx_data = fx_resp.json()

        if "rates" in fx_data and "KRW" in fx_data["rates"]:
            prices["USDKRW"] = fx_data["rates"]["KRW"]
        else:
            print("[FX ERROR] 'rates' missing:", fx_data)

    except Exception as e:
        print("[FX ERROR]", e)

    return jsonify(prices)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
