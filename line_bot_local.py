"""
LINE Bot + Ollama Gemma 4 版
- 接收 LINE 訊息，判斷是否需要搜尋
- 需要搜尋的問題：先搜尋，再讓 Gemma 4 根據搜尋結果回答，並附上來源
- 不需要搜尋的問題：直接讓 Gemma 4 回答
"""

import os
import json
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests

# ===== 設定 =====
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "你的_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "你的_CHANNEL_SECRET")
OLLAMA_MODEL = "gemma2"  # Ollama 上的模型名稱

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# ===== 搜尋功能 =====
def search_web(query: str) -> list:
    """
    使用 DuckDuckGo 搜尋（免 API key）
    回傳搜尋結果列表，每個元素包含 title, url, snippet
    """
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, params={"q": query}, headers=headers, timeout=10)
        resp.raise_for_status()

        results = []
        # 簡單解析 HTML
        from html.parser import HTMLParser

        # 用簡潔的方式抽出結果
        import re
        # 找出所有結果區塊
        blocks = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
                           r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
        for url_match, title, snippet in blocks[:5]:
            # 清理 HTML tags
            title = re.sub(r'<[^>]+>', '', title).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            # 處理 redirect URL
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


# ===== 判斷是否需要搜尋 =====
def need_search(question: str) -> bool:
    """判斷這個問題是否需要搜尋（需要最新資訊）"""
    prompt = f"""你是一個判斷助手。請判斷以下問題是否需要搜尋最新資訊才能回答。
如果問題涉及最近發生的事、今天的新聞、最新資訊、近期變化，請回答「是」。
如果問題是常識、解釋概念、翻譯、數學、歷史知識，請回答「否」。

問題：{question}

請只回答「是」或「否」："""

    try:
        import ollama
        resp = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 10}
        )
        answer = resp["message"]["content"].strip().lower()
        return "是" in answer or "yes" in answer
    except Exception as e:
        logger.error(f"判斷失敗: {e}")
        return False  # 失敗時預設不搜尋


# ===== 用 Ollama Gemma 4 回答 =====
def ask_ollama(question: str, search_results: list = None) -> str:
    """用 Ollama Gemma 4 回答問題，可選擇帶入搜尋結果"""
    import ollama

    if search_results:
        # 組合搜尋結果
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


# ===== LINE Webhook =====
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    logger.info(f"收到 webhook: {body[:200]}...")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    logger.info(f"收到使用者訊息：{user_text}")

    reply_text = ""

    # Step 1: 判斷是否需要搜尋
    try:
        if need_search(user_text):
            logger.info("需要搜尋，開始搜尋...")
            # Step 2: 搜尋
            results = search_web(user_text)
            logger.info(f"搜尋到 {len(results)} 筆結果")
            # Step 3: 用 Ollama 回答（帶入搜尋結果）
            reply_text = ask_ollama(user_text, results)
        else:
            logger.info("不需要搜尋，直接用 Ollama 回答")
            reply_text = ask_ollama(user_text)
    except Exception as e:
        logger.error(f"處理訊息時出錯: {e}")
        reply_text = f"抱歉，處理你的問題時發生錯誤：{str(e)}"

    # 限制回覆長度（LINE 上限 5000 字）
    if len(reply_text) > 4500:
        reply_text = reply_text[:4500] + "\n...(回答過長已截斷)"

    # Step 4: 回覆
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
    logger.info(f"回覆：{reply_text[:100]}...")


@app.route("/")
def home():
    return "LINE Bot with Ollama Gemma 4 is running!"


if __name__ == "__main__":
    from pyngrok import ngrok
    import threading
    import time
    
    port = int(os.environ.get("PORT", 5000))
    
    # 先啟動 bot（在背景執行）
    def run_bot():
        app.run(host="0.0.0.0", port=port, debug=False)
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # 等待 bot 啟動
    time.sleep(2)
    
    # 再建立 ngrok 隧道
    public_url = ngrok.connect(port, "http")
    print(f"\n{'='*50}")
    print(f"ngrok 公開網址: {public_url}")
    print(f"Webhook URL: {public_url}/callback")
    print(f"{'='*50}\n")
    
    # 保持主程式運行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ngrok.kill()
