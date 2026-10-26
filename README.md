# LINE Bot + 本地 Ollama（Apps Script 版）

本專案用 Google Apps Script 當 LINE Webhook 接收端：收到「查 …」的訊息時，轉給跑在自己電腦上的 Ollama（Gemma 2）回答並附來源；其他訊息則記錄到 Google Sheet 當待辦。

---

## 架構

```
LINE
  ↓
Google Apps Script (Webhook, 雲端)
  ↓  「查 …」
轉接站 relay_server.py (自己電腦, port 5001)
  ↓
Ollama Gemma 2 (自己電腦)  →  需要時上網搜尋並附來源
  ↓
回覆 LINE

其他訊息 → Google Sheet（待辦清單）
```

> 因為 Apps Script 在雲端，連不到你電腦的 localhost，所以需要用 ngrok 把「轉接站」變成一個公開網址，讓 Apps Script 呼叫得到。

---

## 怎麼裝

### 1. 安裝 Ollama 與模型

```bash
# Windows 安裝檔：https://ollama.com/download
ollama pull gemma2:2b
ollama serve
```

> 用 `2b` 版本是因為 9b 在你的電腦上（CPU）生成太慢，會讓 LINE 逾時。

### 2. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

`requirements.txt` 內容：

```
flask
requests
ollama
pyngrok
```

### 3. 取得 LINE Channel 資訊

到 [LINE Developers](https://developers.line.biz/) 建立 Messaging API Channel，取得：

- **Channel Access Token**
- **Channel Secret**

---

## 怎麼跑

### 步驟 1：啟動轉接站

先設定 LINE token（轉接站算完答案會**直接回 LINE**）：

```powershell
$env:LINE_CHANNEL_ACCESS_TOKEN = "你的 LINE token"
python relay_server.py
```

它會自動用 pyngrok 建隧道，終端機會印出：

```
==================================================
轉接站啟動中...
Port: 5001
ngrok 公開網址: https://xxxx.ngrok-free.app
==================================================
```

把這個網址記下來。

> 如果 pyngrok 說沒認證，先執行：`ngrok config add-authtoken 你的token`
> （token 在 https://dashboard.ngrok.com/get-started/your-authtoken）

### 步驟 2：建立 Google Apps Script

1. 到 [https://script.google.com/](https://script.google.com/) 建立新專案
2. 把 `Code.gs` 全部貼上
3. 修改最上面兩行設定：

   ```javascript
   const LINE_CHANNEL_ACCESS_TOKEN = "你的 LINE token";
   const RELAY_SERVER_URL = "https://xxxx.ngrok-free.app";  // 步驟 1 的網址，結尾不要加斜線
   ```

4. 儲存
5. **部署 → 新增部署作業 → 網頁應用程式**
   - 執行身分：**我**
   - 存取權：**任何人**
6. 複製部署網址（結尾是 **`/exec`**，不是 `/dev`）

### 步驟 3：設定 LINE Webhook

到 LINE Developers → 你的 Channel → Messaging API：

- **Webhook URL**：直接貼上一步的部署網址（`https://script.google.com/macros/s/..../exec`），**不要再加 `/callback`**
- 點 **Verify**
- **Use webhook** 設為 **Enabled**

> 如果 Verify 出現 302 或 403：通常是貼到 `/dev` 網址，或部署的「存取權」不是「任何人」。

### 步驟 4：測試

| 你傳的訊息 | Bot 的反應 |
|---|---|
| `查 今天有什麼新聞` | 轉給本機 Ollama，上網搜尋後回答並附來源 |
| `買牛奶` | 回「已記錄到待辦」，並寫進 Google Sheet |

> 「查」後面要有空格或直接接問題都可以（程式用 `startsWith("查")` 判斷）。

---

## 檔案說明

| 檔案 | 說明 |
|---|---|
| `Code.gs` | Google Apps Script Webhook：收訊息、判斷是否「查 …」、轉接或寫待辦 |
| `relay_server.py` | 轉接站：收到問題 → Google News RSS + Wikipedia 搜尋 → Ollama Gemma 2 回答 → 回傳並附來源 |
| `line_bot_local.py` | 早期版本：不用 Apps Script，直接在電腦上當 Webhook（備份參考） |
| `cloudflare_worker.js` | 另一種雲端版本（改用 Gemini API，不需本機 Ollama） |
| `requirements.txt` | Python 依賴套件 |

---

## 我改了什麼

- 把 Webhook 放在 **Google Apps Script**，讓 LINE 不需要直接連到本機。
- 新增 **轉接站 `relay_server.py`**：接收 Apps Script 的 `/ask` 請求，先上網搜尋，再交給本機 Ollama 回答，並在答案最後附上來源網址。
- 搜尋來源改用 **Google News RSS + 中文 Wikipedia API**（原本的 DuckDuckGo 會被反機器人頁面擋掉，回傳 0 筆）。
- 模型改用 **gemma2:2b**：原本的 gemma2:9b 在這台電腦（純 CPU、記憶體有限）生成太慢，會超過 LINE 的回覆時限；2b 明顯快很多，且同樣是 Gemma 2 系列。
- 改成**非同步回覆**：Apps Script 收到「查 …」會立刻回 200（避免 LINE webhook 逾時），轉接站算完後**直接呼叫 LINE Reply API** 回覆。
- 來源網址改用**媒體首頁**（Google News 的文章連結又長又會轉址），畫面比較乾淨。
- 訊息分流：**「查 …」走 AI 回答**，其他訊息**寫進 Google Sheet 當待辦**。
- 轉接站內建 **pyngrok 自動建隧道**，啟動時直接印出可用的公開網址，不用另外開一個 ngrok 視窗。
- `doPost` 加上空值檢查，避免 LINE 的驗證請求造成錯誤。

---

## 卡住時檢查

1. `ollama list` 要看到 `gemma2:2b`
2. 轉接站視窗要印出 `ngrok 公開網址: ...`
3. 用瀏覽器開 `https://你的ngrok網址/` 應該看到「轉接站運行中！」
4. Apps Script 部署的存取權一定要是「任何人」，否則 LINE Verify 會出現 403 / 302
5. Webhook URL 要用 `/exec` 結尾的部署網址，不能用 `/dev`（`/dev` 一定要登入，會回 302）
6. 轉接站啟動時要顯示 `LINE token: 已設定`，否則「查 …」不會有回覆
