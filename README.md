# LINE Bot + 本地 Ollama（Apps Script 版）

本專案使用 Google Apps Script 作為 LINE Webhook 接收器，收到「查 ...」的訊息時，轉給跑在電腦上的 Ollama Gemma 2 模型回答；其他訊息記錄到 Google Sheet 待辦。

---

## 架構

```
LINE → Google Apps Script (Webhook) → 轉接站 (你電腦, port 5001) → Ollama Gemma 2
                                                        ↓
                                              其他訊息 → Google Sheet (待辦)
```

---

## 部署步驟

### 1. 申請 Gemini API Key（不需要了，改用 Ollama）
> 本專案使用 Ollama，不需要 Gemini API

### 2. 設定 Ollama
```bash
ollama pull gemma2
ollama serve
```

### 3. 啟動轉接站
```powershell
pip install flask requests ollama
python relay_server.py
```

### 4. 建立 ngrok 隧道
```powershell
ngrok http 5001
```
把 ngrok 給的網址記下來，例如 `https://xxxx.ngrok-free.app`

### 5. 建立 Google Apps Script
1. 前往 [https://script.google.com/](https://script.google.com/) 建立新專案
2. 把 `Code.gs` 的內容貼上
3. 修改設定：
   - `LINE_CHANNEL_ACCESS_TOKEN` → 你的 LINE token
   - `RELAY_SERVER_URL` → 你的 ngrok 網址（不含 /ask）
4. 部署為 Web App（執行身份：我，存取權：任何人）
5. 把部署後的 URL + `/callback` 貼到 LINE Developers 的 Webhook URL

### 6. 測試
- 傳「查今天新聞」→ bot 用 Ollama 回答，附來源
- 傳「買牛奶」→ bot 記錄到 Google Sheet 待辦

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `Code.gs` | Google Apps Script Webhook（接收 LINE 訊息、判斷轉發） |
| `relay_server.py` | 轉接站程式（接收請求、搜尋、Ollama 回答） |
| `README.md` | 本文件 |
| `requirements.txt` | Python 依賴套件 |

---

## 注意事項

- 確認 Ollama 正在運行（`ollama serve`）
- 確認轉接站在運行（`python relay_server.py`）
- 確認 ngrok 隧道已建立（`ngrok http 5001`）
- LINE Channel 的 Webhook 已啟用
- 回覆長度上限 5000 字（LINE 限制）
