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
def search_web(query: str) -> list:
    """使用 DuckDuckGo 搜尋（免 API key）"""
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, params={"q": query}, headers=headers, timeout=10)
        resp.raise_for_status()

        results = []
        import re
        blocks = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
                           r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
        for url_match, title, snippet in blocks[:5]:
            title = re.sub(r'<[^>]+>', '', title).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            if "uddg=" in url_match:
                import urllib.parse
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url_match).query)
                if "uddg" in parsed:
                    url_match = parsed["uddg"][0]
            results.append({"title": title, "url": url_match, "snippet": snippet})
        return results
    except Exception as e:
        logger.error(f"搜尋失敗: {e}")
        return []


# ===== 用 Ollama Gemma 2 回答 =====
def ask_ollama(question: str, search_results: list = None) -> str:
    """用 Ollama Gemma 2 回答問題，可選擇帶入搜尋結果"""
    import ollama

    if search_results:
        context = "\n\n".join([
            f"[{i+1}] {r['title']}\n{r['snippet']}\n來源：{r['url']}"
            for i, r in enumerate(search_results)
        ])
        user_content = f"""以下是搜尋結果，請根據這些資訊回答使用者的問題，並在回答的最後附上來源網址：

搜尋結果：
{context}

使用者問題：{question}

請用繁體中文回答，回答的最後一行請附上來源網址（格式：來源：網址）。"""
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
    logger.info(f"回答：{answer[:100]}...")
    
    return jsonify({"answer": answer})


@app.route("/")
def home():
    return "轉接站運行中！Ollama Gemma 2 已就緒。"


if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"轉接站啟動中...")
    print(f"Port: {PORT}")
    print(f"請用 ngrok 建立隧道：ngrok http {PORT}")
    print(f"{'='*50}\n")
    
    app.run(host="0.0.0.0", port=PORT, debug=True)
