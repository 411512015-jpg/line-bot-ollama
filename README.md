# LINE Bot + Gemini API

本專案是一支 LINE 聊天機器人，使用 Google Gemini API 回答問題，並記錄到 Google Sheet。

---

## 功能

- 接收 LINE 訊息
- 用 Google Gemini API 回答問題
- 自動記錄對話到 Google Sheet
- 完全雲端运行，不需要本機伺服器

---

## 部署方式

### 1. 取得 Gemini API Key
前往 [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) 免費申請

### 2. 建立 Google Apps Script
1. 前往 [https://script.google.com/](https://script.google.com/) 建立新專案
2. 把 `google_apps_script.gs` 的內容貼上
3. 修改設定：
   - `GEMINI_API_KEY` → 你的 API key
   - `LINE_CHANNEL_ACCESS_TOKEN` → 你的 LINE token

### 3. 部署為 Web App
1. 點擊「部署」→「新增部署作業」
2. 選擇「網頁應用程式」
3. 執行身份：選「我」
4. 存取權：選「任何人」
5. 點擊「部署」

### 4. 設定 LINE Webhook
把部署後的 URL + `/callback` 貼到 LINE Developers 的 Webhook URL

### 5. 測試
用手機 LINE 傳訊息給 bot

---

## 替代方案：本機端 Ollama

如果你想要使用本機端 Ollama Gemma 模型，請參考 `line_bot_local.py`。

---

## 安裝與使用

### 1. 安裝 Ollama 與 Gemma 4

```bash
# 安裝 Ollama（Windows 安裝檔）
# 下載：https://ollama.com/download

# 拉取 Gemma 4 模型
ollama pull gemma4

# 啟動 Ollama（確認在背景運行）
ollama serve
```

### 2. 安裝 LINE Bot 依賴

```bash
pip install -r requirements.txt
```

### 3. 設定 LINE Developers

1. 前往 [LINE Developers](https://developers.line.biz/) 建立一個新的 Provider 和 Channel（Messaging API）
2. 取得 **Channel Access Token** 和 **Channel Secret**
3. 設定環境變數：

```bash
# Windows PowerShell
$env:LINE_CHANNEL_ACCESS_TOKEN = "你的token"
$env:LINE_CHANNEL_SECRET = "你的secret"
```

### 4. 設定 Webhook URL

在 LINE Developers 後台設定 Webhook URL，指向你的公開網址（可使用 ngrok 做本地測試）：

```bash
# 安裝 ngrok 後執行
ngrok http 5000
```

將 `https://你的ngrok網址/callback` 貼到 LINE Developers 的 Webhook URL 欄位。

### 5. 啟動 Bot

```bash
python line_bot_local.py
```

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `line_bot_local.py` | Bot 主程式（接收訊息、搜尋、Ollama 回答） |
| `requirements.txt` | Python 依賴套件 |
| `README.md` | 本文件 |

---

## 運作流程

```
使用者傳訊息
    ↓
LINE Webhook 接收
    ↓
Gemma 4 判斷是否需要搜尋？
    ↓              ↓
  不需要        需要搜尋
    ↓              ↓
直接回答     搜尋網路
    ↓              ↓
    ←  Gemma 4 根據搜尋結果回答 + 來源網址
    ↓
回覆使用者
```

---

## 注意事項

- 確認 Ollama 正在運行（`ollama serve`）
- 確認 Gemma 4 模型已下載（`ollama pull gemma4`）
- LINE Channel 的 Webhook 已啟用
- 回覆長度上限 5000 字（LINE 限制）
