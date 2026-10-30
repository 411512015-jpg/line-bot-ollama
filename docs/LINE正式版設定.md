# LINE 正式版設定指南（token + ngrok → Apps Script → LINE）

> 這個文件記錄「正式 LINE 版」的設定步驟；課堂 demo 不需要正式版，走 `http://127.0.0.1:5001/demo` 即可。

## 前置條件

- [ ] Ollama 已安裝並 `ollama pull gemma2:2b` + `ollama serve`
- [ ] ngrok 已安裝，並已登入 ngrok 帳號（`ngrok authtoken <token>`）
- [ ] Google 帳號已連 LINE Developers

## 步驟 1：取得 LINE Channel Access Token

1. 到 [LINE Developers Console](https://developers.line.biz/) → 建立 Messaging API Channel
2. 取得 **Channel Access Token**（長字串）
3. 記下來，之後放進 Apps Script 指令碼屬性

## 步驟 2：建立 ngrok 隧址

```powershell
ngrok http 5001
```

→ 記下 `https://xxxx.ngrok-free.app`（結尾不要加斜線）

## 步驟 3：Apps Script 設定

1. [script.google.com](https://script.google.com/) → 貼上 `Code.gs`
2. **專案設定 → 指令碼屬性**，新增：
   - `LINE_CHANNEL_ACCESS_TOKEN` = 你的 Channel Access Token
   - `RELAY_SERVER_URL` = ngrok 網址（如 `https://xxxx.ngrok-free.app`）
3. 編輯器執行 `checkConfig` → 應顯示「轉接站：…」「LINE token：已設定」
4. **部署 → 新增部署作業 → 網頁應用程式**：執行身分：**我**，存取權：**任何人**
5. 把部署網址貼到 LINE Developers → Messaging API → **Webhook URL**
6. 點 **Verify**，並把 **Use webhook** 設為 **Enabled**

## 步驟 4：正式版功能驗證

- [ ] LINE 傳 `咖啡 45 元` → Bot 回「已記帳…今日累計…本月累計…上個月累計…」
- [ ] LINE 傳 `Uber 60` → 分類更新為交通
- [ ] LINE 傳 `買牛奶` → 寫入 Google Sheet 待辦
- [ ] LINE 傳 `查 玉山有多高` → 回答案＋來源
- [ ] 關閉本機轉接站 → LINE 端有錯誤提示，不會永久轉圈

## 注意事項

- ngrok 免費網址**重開會換** → 換了要重新更新 Apps Script 的 `RELAY_SERVER_URL`
- token 過期／外洩 → 重新發行，舊的直接失效
- token 只放指令碼屬性，**不進 repo**

## 交件前安全檢查

```powershell
python scripts/check_submission.py
```
