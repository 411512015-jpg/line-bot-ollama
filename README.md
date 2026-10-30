# LINE × 本地 AI 記帳小幫手

> 同一個 LINE 聊天視窗，記一筆就花掉錢；想查資料就問 AI。

![課堂展示頁](docs/screenshots/demo-answer.png)

## 30 秒看懂

| 你傳的訊息 | Bot 做的事 |
|---|---|
| `咖啡 45 元` | 本地解析 merchant（咖啡）＋ amount（45 元）→ 分類「飲食」→ 回覆今日／本月累計 |
| `全聯 300 早餐` | 同上 → 分類「飲食」，累計更新 |
| `Uber 60` | 同上 → 分類「交通」，累計更新 |
| `查 玉山有多高` | 搜尋中文 Wikipedia，交給本機 Gemma 2 整理，回覆附上來源 |

這個專案解決的不是「再做一個聊天機器人」，而是：

1. **記帳不想開 App、不想手動打分類**：在 LINE 裡一句話「咖啡 45 元」，就自動分類、累計。
2. **不想把每句話都送給雲端模型**：記帳只做本地解析＋本地加總，完全免 API 費用。
3. **AI 的「查」功能保留**：想查資料就打「查 …」，答案跟來源一起回來。

主要使用者：**手機不離身、常用 LINE 的學生與小型團隊**；也適合想玩本地 LLM、但不想付 API 費用的記帳者。

---

## 架構

![架構圖](docs/screenshots/architecture.png)

```text
LINE
  │  使用者傳「咖啡 45 元」或「查 …」
  ▼
Google Apps Script（雲端 Webhook）
  │  「查 …」或「咖啡 45 元」→ 非同步轉給轉接站
  │  其他訊息 → 寫入 Google Sheet
  ▼
Flask 轉接站（自己的電腦，port 5001）
  │  1. 「咖啡 45 元」→ 本地 parse_expense（merchant + amount + category）
  │  2. 「查 …」→ 搜尋（Google News RSS／中文 Wikipedia）+ Ollama
  ▼
Ollama Gemma 2 2B（本機 CPU 推論）
  │  「查 …」→ 回覆附來源；「咖啡 45 元」→ 分類＋累計
  ▼
LINE Reply API → 回覆使用者
```

### 為什麼這樣設計？

- **Apps Script 當 Webhook**：不用自己養一台 24 小時的雲端主機，LINE 的驗證請求也有免費的 HTTPS 端點可以接。
- **Flask 轉接站**：Apps Script 連不到 `localhost`，所以用 ngrok 把本機的 Flask 變成公開網址；真正搜尋與推論都在本機。
- **Gemma 2 2B**：9B 在這台純 CPU 電腦上生成太慢，會超過 LINE 的回覆時限；2B 明顯快很多。
- **先搜尋、再回答**：把搜尋結果放進 prompt，要求模型「只使用搜尋結果」，並在答案後附來源，降低幻覺。
- **非同步回覆**：Apps Script 收到訊息立刻回 200，轉接站算完再由背景執行緒呼叫 LINE Reply API，避免 Webhook 逾時。
- **本地記帳引擎**：「咖啡 45 元」由本地正規表示式解析 merchant 與金額，依關鍵字分類（飲食／交通／娛樂／醫療／其他），累計只需純計算，不碰任何 API。

---

## 課堂 90 秒 Demo

### 最快的方式：展示頁（不需要 LINE token）

1. 確認 Ollama 已安裝，且已下載模型：

   ```powershell
   ollama pull gemma2:2b
   ollama serve
   ```

2. 雙擊 `start_demo.bat`，瀏覽器會開啟 `http://127.0.0.1:5001/demo`。

3. 依序點擊或輸入：

   - `咖啡 45 元`
   - `全聯 300 早餐`
   - `Uber 60`

展示頁和 LINE 版共用同一個 `/ask` 流程，差別只在回覆通道：展示頁用瀏覽器，LINE 版用 Reply API。展示頁的支出寫入本機 `expenses.txt`；正式 LINE 版寫入 Google Sheet。

### 真的接上 LINE

#### 1. 安裝 Python 套件

```powershell
pip install -r requirements.txt
```

#### 2. 啟動轉接站

先到 LINE Developers 建立 Messaging API Channel，取得 **Channel Access Token**。不要把 token 寫進程式碼，使用環境變數：

```powershell
$env:LINE_CHANNEL_ACCESS_TOKEN = "你的 token"
$env:OLLAMA_MODEL = "gemma2:2b"
python relay_server.py
```

#### 3. 建立 Apps Script Webhook

1. 到 [script.google.com](https://script.google.com/) 建立新專案，貼上 `Code.gs`。
2. 到 **專案設定 → 指令碼屬性**，新增兩筆：

   | 屬性 | 值 |
   |---|---|
   | `LINE_CHANNEL_ACCESS_TOKEN` | 你的 Channel Access Token |
   | `RELAY_SERVER_URL` | 上一步的 ngrok 網址，結尾不要斜線 |

3. 在編輯器執行 `checkConfig`，確認顯示「LINE token：已設定」。
4. **部署 → 新增部署作業 → 網頁應用程式**：執行身分：**我**，存取權：**任何人**。
5. 複製「網頁應用程式」的正式部署網址，貼到 LINE Developers → Messaging API → **Webhook URL**。
6. 點 **Verify**，並把 **Use webhook** 設為 **Enabled**。

#### 4. Google Sheet 支出記錄

不需要手動建立試算表。第一次收到「咖啡 45 元」這類記帳格式時，`Code.gs` 會自動把支出寫入 Google Sheet（欄位：時間、使用者 ID、支出項目、金額、分類），並記住試算表 ID。

---

## 測試

### 單元測試（不需要 LINE token 或 Ollama）

```powershell
python -m unittest discover -s tests -v
```

目前 **17 個測試**，涵蓋：

- `clean_query` 是否正確移除「查／查詢／請問」等口語前綴。
- 新聞類問題是否優先走 Google News，知識類是否優先走 Wikipedia。
- 回答是否附上「來源：」，沒有搜尋結果時是否能正常回覆。
- `/ask` 在沒有 `replyToken` 時是否同步回 JSON。
- `/demo/message` 的查詢／記帳／待辦分流與空訊息檢查。
- `/demo/expenses` 是否正確回支出清單與今日／本月累計。
- 記帳解析（`parse_expense`）是否正確處理「咖啡 45 元」、排除「買牛奶」這類無金額文字。
- `/health` 是否意外洩漏 token。

### 本機實測（Windows 11、Python 3.13、CPU 推論）

| 情境 | 結果 |
|---|---:|
| 記帳回覆（暖機後） | 今日累計／本月累計即時更新，約 0.3 秒 |
| 冷啟動（模型尚未載入） | **16.2 秒**（主要花在載入模型） |

### 手動 End-to-End 檢查清單

- [ ] `ollama list` 看得到 `gemma2:2b`。
- [ ] 展示頁輸入 `咖啡 45 元` → Bot 回「已記帳…今日累計…本月累計…」。
- [ ] 展示頁輸入 `Uber 60` → 分類「交通」，累計更新。
- [ ] LINE 傳「咖啡 45 元」→ Google Sheet 新增一列，Bot 回累計。
- [ ] 關掉轉接站時，LINE 端有錯誤提示，不會永久轉圈。

### 交件前安全檢查

```powershell
python scripts/check_submission.py
```

---

## 安全與隱私

- **不要把 token 寫進 repo**。本機用環境變數；Apps Script 用「指令碼屬性」。
- `.gitignore` 已排除 `.env`、`Code_filled.gs`、`start_local.bat`、`todo.txt`、`expenses.txt` 等本機檔案。
- 如果 token 曾經出現在對話、截圖或 commit，請立刻到 LINE Developers **重新發行 token**，舊 token 直接失效。
- 報告、投影片、截圖上傳前，請再人工檢查一次網址列、終端機與程式碼畫面。
- 這個架構不是「全部離線」：記帳路徑完全在本地；「查 …」問題會經過 LINE、Google Apps Script 與公開搜尋服務；只有模型推論在本機。若資料敏感，請不要傳給 Bot。

---

## 已知限制

1. **電腦要開著**：關機、休眠或 Ollama 沒開，LINE 就記不了帳。
2. **ngrok 免費網址會變**：每次重開都要更新 Apps Script 的 `RELAY_SERVER_URL`。
3. **記帳分類是關鍵字 heuristic**：「全聯 300 早餐」分類成「飲食」；未來要改成 AI 分類或使用者自訂類別。
4. **累計只在本機**：多人使用時要考慮共用資料來源（例如 Google Sheet）。
5. **尚未驗證 LINE 簽章**：公開部署後，任何人知道網址都能送假事件。下一步應驗證 `X-Line-Signature` 或加上來源限制。

---

## 下一步

- 用 AI（或 LLM）做更細的分類：消費者行為分析、預算警示、超標通知。
- 把回覆做成 LINE Flex Message，讓來源／圖表更清楚。
- 把累計畫成 LINE Flex Card 圖表，或串 Google Sheets／BigQuery 匯總。
- 在 Apps Script 加入 **LINE 簽章驗證**與 allowlist。
- 搜尋改成「先抓文章正文，再切 chunk 做 RAG」。

---

## 檔案說明

| 檔案 | 說明 |
|---|---|
| `Code.gs` | Google Apps Script Webhook：讀指令碼屬性、分流（查／記帳／待辦）、非同步轉接、寫 Google Sheet |
| `relay_server.py` | Flask 轉接站：記帳解析、搜尋、Ollama、附來源、LINE Reply、展示頁 |
| `templates/demo.html` | 課堂展示頁（手機版聊天 UI＋流程面板） |
| `static/demo.css`、`static/demo.js` | 展示頁樣式與互動 |
| `tests/test_relay.py` | 不需外部服務的單元測試 |
| `scripts/check_submission.py` | 交件前的敏感資料掃描 |
| `scripts/generate_assets.py` | 產生報告用架構圖 |
| `docs/` | 專題報告、AI 對話摘要、投影片、90 秒腳本與截圖 |
| `requirements.txt` | Python 依賴套件 |

---

## 開發過程

這個專案是與 AI 編程助理一起迭代完成的：先做 Cloudflare Worker + Gemini 版本，發現需要 API key 與額度；再改成 Apps Script + 本機 Ollama；接著把「查資料」流程打磨到附來源、又加入了「記帳」模式。完整的除錯紀錄與 prompt 整理在 [`docs/AI對話摘要.md`](docs/AI對話摘要.md)。
