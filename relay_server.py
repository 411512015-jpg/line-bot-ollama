"""
轉接站程式 - 接收 Apps Script 的請求，轉給本地 Ollama 回答
- 接收 POST /ask 請求
- 用 Ollama Gemma 2 回答問題
- 傳回答案給 Apps Script
"""

import os
import json
import logging
from flask import Flask, request, jsonify
import requests

# ===== 設定 =====
OLLAMA_MODEL = "gemma2"  # Ollama 上的模型名稱
PORT = 5001  # 轉接站的 port

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== 搜尋功能 =====
def _search_google_news(query: str, limit: int = 4) -> list:
    """Google News RSS：適合查「今天/最新」的新聞，穩定免金鑰"""
    try:
        from urllib.parse import quote
        import xml.etree.ElementTree as ET

        url = (
            "https://news.google.com/rss/search?q="
            + quote(query)
            + "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        )
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        results = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            if title and link:
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": f"發布時間：{pub}" if pub else "",
                })
            if len(results) >= limit:
                break
        return results
    except Exception as e:
        logger.error(f"Google News 搜尋失敗: {e}")
        return []


def _search_wikipedia(query: str, limit: int = 3) -> list:
    """Wikipedia API：適合查知識型問題，穩定免金鑰"""
    try:
        import re
        import urllib.parse

        resp = requests.get(
            "https://zh.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": limit,
            },
            headers={"User-Agent": "line-bot-relay/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("query", {}).get("search", []):
            title = item["title"]
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", "")).strip()
            results.append({
                "title": title,
                "url": "https://zh.wikipedia.org/wiki/" + urllib.parse.quote(title),
                "snippet": snippet,
            })
        return results
    except Exception as e:
        logger.error(f"Wikipedia 搜尋失敗: {e}")
        return []


def search_web(query: str) -> list:
    """
    組合搜尋：Google News RSS + Wikipedia（皆免 API key、不易被封鎖）
    """
    results = _search_google_news(query, limit=4)
    results += _search_wikipedia(query, limit=3)

    # 去重
    seen, unique = set(), []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique[:5]


# ===== 用 Ollama Gemma 2 回答 =====
def ask_ollama(question: str, search_results: list = None) -> str:
    """用 Ollama Gemma 2 回答問題，可選擇帶入搜尋結果"""
    import ollama

    if search_results:
        context = "\n\n".join([
            f"[{i+1}] {r['title']}\n{r['snippet']}\n來源：{r['url']}"
            for i, r in enumerate(search_results)
        ])
        user_content = f"""以下是搜尋結果，請根據這些資訊回答使用者的問題：

搜尋結果：
{context}

使用者問題：{question}

請用繁體中文回答，重點清楚、不要編造搜尋結果以外的內容。"""
    else:
        user_content = f"請用繁體中文回答以下問題：\n\n{question}"

    resp = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": "你是一個有幫助的助手。請用繁體中文回答問題。"},
            {"role": "user", "content": user_content}
        ],
        options={"temperature": 0.7, "num_predict": 500}
    )
    return resp["message"]["content"].strip()


# ===== 轉接站 API =====
@app.route("/ask", methods=["POST"])
def ask():
    """接收 Apps Script 的請求，轉給 Ollama 回答"""
    data = request.get_json()
    question = data.get("question", "")
    
    logger.info(f"收到問題：{question}")
    
    # 搜尋網路
    search_results = search_web(question)
    logger.info(f"搜尋到 {len(search_results)} 筆結果")
    
    # 用 Ollama 回答
    answer = ask_ollama(question, search_results)

    # 有搜尋結果就強制附上來源（不依賴模型自己記得）
    if search_results:
        sources = "\n".join(
            f"{i+1}. {r['title'][:40]} - {r['url']}"
            for i, r in enumerate(search_results[:3])
        )
        answer = f"{answer}\n\n來源：\n{sources}"

    logger.info(f"回答：{answer[:100]}...")
    
    return jsonify({"answer": answer})


@app.route("/")
def home():
    return "轉接站運行中！Ollama Gemma 2 已就緒。"


if __name__ == "__main__":
    from pyngrok import ngrok
    import threading
    import time
    
    # 先啟動 bot（在背景執行）
    def run_server():
        app.run(host="0.0.0.0", port=PORT, debug=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 等待 bot 啟動
    time.sleep(2)
    
    # 再建立 ngrok 隧道
    public_url = ngrok.connect(PORT, "http")
    print(f"\n{'='*50}")
    print(f"轉接站啟動中...")
    print(f"Port: {PORT}")
    print(f"ngrok 公開網址: {public_url}")
    print(f"{'='*50}\n")
    
    # 保持主程式運行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ngrok.kill()
