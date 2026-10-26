"""
轉接站程式 - 接收 Apps Script 的請求，轉給本地 Ollama 回答
- 接收 POST /ask 請求
- 用 Ollama Gemma 2 回答問題
- 傳回答案給 Apps Script
"""

import os
import sys
import json
import logging
from flask import Flask, request, jsonify
import requests

# Windows 終端機強制 UTF-8，避免中文變亂碼
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ===== 設定 =====
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma2:2b")  # Ollama 上的模型名稱（2b 版本在 CPU 上比較快）
PORT = 5001  # 轉接站的 port
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")  # 轉接站直接回 LINE 用

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
            src = item.find("source")
            src_name = (src.text or "").strip() if src is not None else ""
            src_url = (src.get("url") or "").strip() if src is not None else ""

            # 標題結尾常是「 - 媒體名」，去掉讓畫面乾淨
            if src_name and title.endswith(" - " + src_name):
                title = title[: -(len(src_name) + 3)]

            # 用媒體首頁當來源（Google News 的文章連結又長又會轉址）
            source_url = src_url or link

            # 社群連結不適合當新聞來源，跳過
            if any(d in source_url for d in ["facebook.com", "twitter.com", "x.com", "instagram.com", "threads.net"]):
                continue

            if title and source_url:
                results.append({
                    "title": f"{title}（{src_name}）" if src_name else title,
                    "url": source_url,
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


NEWS_HINTS = [
    "新聞", "最新", "今天", "今日", "近期", "最近", "現在", "目前",
    "股價", "匯率", "天氣", "颱風", "選舉", "開票", "疫情", "發表",
]


def clean_query(query: str) -> str:
    """把「查 …」口語問題清成適合搜尋的關鍵字"""
    import re

    q = (query or "").strip()
    q = re.sub(r"^查\s*", "", q)
    for w in ["請問", "幫我查", "幫我", "查一下", "查詢", "告訴我"]:
        q = q.replace(w, "")
    q = re.sub(
        r"(有多高|有多長|有多大|有多重|有多遠|是多少|是什麼|是誰|在哪裡|在哪|"
        r"怎麼走|怎麼辦|為什麼|如何|多少錢|多少|幾歲|嗎|呢|？|\?)",
        "",
        q,
    )
    return q.strip()


def search_web(query: str) -> list:
    """
    依問題類型選來源：
    - 有「新聞/最新/今天…」→ Google News 優先
    - 其他（知識型）→ 中文 Wikipedia 優先
    兩者都免 API key，且比 DuckDuckGo 穩定。
    """
    cq = clean_query(query) or query
    is_news = any(h in query for h in NEWS_HINTS)

    results = []
    if is_news:
        results += _search_google_news(cq, limit=3)
        results += _search_wikipedia(cq, limit=2)
    else:
        results += _search_wikipedia(cq, limit=3)
        results += _search_google_news(cq, limit=2)

    # 去重
    seen, unique = set(), []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique[:4]


# ===== 用 Ollama Gemma 2 回答 =====
def ask_ollama(question: str, search_results: list = None) -> str:
    """用 Ollama Gemma 2 回答問題，可選擇帶入搜尋結果"""
    import ollama

    if search_results:
        context = "\n\n".join([
            f"[{i+1}] {r['title']}\n{r['snippet'][:200]}"
            for i, r in enumerate(search_results[:3])
        ])
        user_content = f"""以下是搜尋結果，請根據這些資訊回答使用者的問題：

搜尋結果：
{context}

使用者問題：{question}

請用繁體中文、重點式回答（不要條列太多）。只使用搜尋結果裡有的事實；若找不到答案，就直接說「查不到」。"""
    else:
        user_content = f"請用繁體中文回答以下問題：\n\n{question}"

    resp = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": "你是一個有幫助的助手。請用繁體中文回答問題，回答盡量精簡。"},
            {"role": "user", "content": user_content}
        ],
        options={"temperature": 0.5, "num_predict": 220, "num_ctx": 2048},
        keep_alive="30m"
    )
    return resp["message"]["content"].strip()


# ===== 轉接站 API =====
def build_answer(question: str) -> str:
    """搜尋 + Ollama 回答 + 附來源"""
    import time as _time

    t0 = _time.time()
    search_results = search_web(question)
    t1 = _time.time()
    logger.info(f"搜尋到 {len(search_results)} 筆結果（{t1 - t0:.1f} 秒）")

    answer = ask_ollama(question, search_results[:3])
    t2 = _time.time()
    logger.info(f"Ollama 產生完成（{t2 - t1:.1f} 秒）")

    if search_results:
        sources = "\n".join(
            f"{i+1}. {r['title'][:50]}\n   {r['url']}"
            for i, r in enumerate(search_results[:3])
        )
        answer = f"{answer}\n\n來源：\n{sources}"

    logger.info(f"總耗時 {_time.time() - t0:.1f} 秒")
    return answer


def reply_line(reply_token: str, text: str):
    """轉接站直接呼叫 LINE Reply API"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not reply_token:
        logger.warning("沒有 LINE token 或 replyToken，無法直接回覆")
        return
    if len(text) > 4500:
        text = text[:4500] + "\n...(已截斷)"
    try:
        resp = requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={
                "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"replyToken": reply_token, "messages": [{"type": "text", "text": text}]},
            timeout=15,
        )
        logger.info(f"已回覆 LINE（HTTP {resp.status_code}）")
        if resp.status_code != 200:
            logger.error(f"LINE 回覆失敗內容：{resp.text[:300]}")
    except Exception as e:
        logger.error(f"回覆 LINE 失敗: {e}")


# ===== 轉接站 API =====
@app.route("/ask", methods=["POST"])
def ask():
    """
    有 replyToken → 立刻回 202，背景算完再直接回 LINE（避免 LINE webhook 逾時）
    沒有 replyToken → 同步回答案（方便本機測試）
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    reply_token = data.get("replyToken")

    logger.info(f"收到問題：{question}")

    if reply_token:
        def worker():
            try:
                answer = build_answer(question)
                logger.info(f"回答：{answer[:120]}...")
                reply_line(reply_token, answer)
            except Exception as e:
                logger.error(f"處理問題失敗: {e}")
                reply_line(reply_token, f"抱歉，處理時發生錯誤：{e}")

        import threading
        threading.Thread(target=worker, daemon=True).start()
        return jsonify({"status": "accepted"}), 202

    answer = build_answer(question)
    logger.info(f"回答：{answer[:120]}...")
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

    # 預先載入模型，避免第一次提問等太久
    def warm_up():
        try:
            import ollama
            logging.info("預先載入 Ollama 模型...")
            ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": "你好"}],
                options={"num_predict": 1, "num_ctx": 2048},
                keep_alive="30m",
            )
            logging.info("模型已載入完成")
        except Exception as e:
            logging.error(f"預先載入模型失敗: {e}")

    threading.Thread(target=warm_up, daemon=True).start()

    # 再建立 ngrok 隧道
    public_url = ngrok.connect(PORT, "http")
    print(f"\n{'='*50}")
    print(f"轉接站啟動中...")
    print(f"Port: {PORT}")
    print(f"模型: {OLLAMA_MODEL}")
    print(f"LINE token: {'已設定（可直接回 LINE）' if LINE_CHANNEL_ACCESS_TOKEN else '未設定（只會回傳答案，不會自己回 LINE）'}")
    print(f"ngrok 公開網址: {public_url}")
    print(f"{'='*50}")
    print("\n等待 LINE 訊息中... （這個視窗請保持開啟）\n")
    
    # 保持主程式運行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ngrok.kill()
