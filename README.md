# LINE 待辦 × 本地 AI 查詢助手

> 同一個 LINE 聊天視窗，兩種工作流：**「查 …」**交給本機 Ollama 搜尋＋回答並附來源；**其他訊息**自動記成待辦。

![課堂展示頁](docs/screenshots/demo-answer.png)

## 30 秒看懂

| 你傳的訊息 | Bot 做的事 |
|---|---|
| `查 玉山有多高` | 搜尋中文 Wikipedia，交給本機 Gemma 2 整理，回覆附上來源 |
| `查 今天台灣有什麼新聞` | 搜尋 Google News RSS，整理近期新聞，回覆附上媒體來源 |
| `買牛奶` | 寫入 Google Sheet 待辦清單，回覆「已記錄到待辦」 |

這個專案解決的不是「再做一個聊天機器人」，而是：

1. **查資料要切換 App**：在 LINE 裡直接問，答案跟來源一起回來。
2. **待辦散在聊天記錄裡**：不用另外開記事軟體，隨手一句就記下來。
3. **不想把每句話都送給雲端模型**：推論跑在自己的電腦，沒有逐字 API 費用。

主要使用者：**手機不離身、常用 LINE 的學生與小型團隊**；也適合想玩本地 LLM、但不想先買 GPU 的人。

---

## 架構

![架構圖](docs/screenshots/architecture.png)

```text
LINE
  │  使用者傳「查 …」或待辦
  ▼
Google Apps Script（雲端 Webhook）
  │  「查 …」→ 非同步轉給轉接站
  │  其他訊息 → 寫入 Google Sheet
  ▼
Flask 轉接站（自己的電腦，port 5001）
  │  1. Google News RSS／中文 Wikipedia 搜尋
  │  2. 整理搜尋結果，交給 Ollama
  ▼
Ollama Gemma 2 2B（本機 CPU 推論）
  │
  ▼
LINE Reply API → 回覆使用者（附來源）
```

### 為什麼這樣設計？

- **Apps Script 當 Webhook**：不用自己養一台 24 小時的雲端主機，LINE 的驗證請求也有免費的 HTTPS 端點可以接。
- **Flask 轉接站**：Apps Script 連不到 `localhost`，所以用 ngrok 把本機的 Flask 變成公開網址；真正搜尋與推論都在本機。
- **Gemma 2 2B**：9B 在這台純 CPU 電腦上生成太慢，會超過 LINE 的回覆時限；2B 明顯快很多。
- **先搜尋、再回答**：把搜尋結果放進 prompt，要求模型「只使用搜尋結果」，並在答案後附來源，降低幻覺。
- **非同步回覆**：Apps Script 收到訊息立刻回 200，轉接站算完再由背景執行緒呼叫 LINE Reply API，避免 Webhook 逾時。

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

   - `查 玉山有多高`
   - `買牛奶`

展示頁和 LINE 版共用同一個 `/ask` 流程，差別只在回覆通道：展示頁用瀏覽器，LINE 版用 Reply API。展示頁的待辦寫入本機 `todo.txt`；正式 LINE 版寫入 Google Sheet。

> 如果不想用 `.bat`，也可以手動執行：
>
> ```powershell
> $env:LOCAL_ONLY = "1"
> $env:OLLAMA_MODEL = "gemma2:2b"
> python relay_server.py
> ```

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

終端機會印出：

```text
轉接站啟動中...
Port: 5001
模型: gemma2:2b
LINE token: 已設定（可直接回 LINE）
ngrok 公開網址: https://xxxx.ngrok-free.app
```

記下 ngrok 網址。免費方案重開會換網址，換了就要更新 Apps Script 的設定。

#### 3. 建立 Apps Script Webhook

1. 到 [script.google.com](https://script.google.com/) 建立新專案，貼上 `Code.gs`。
2. 到 **專案設定 → 指令碼屬性**，新增兩筆：

   | 屬性 | 值 |
   |---|---|
   | `LINE_CHANNEL_ACCESS_TOKEN` | 你的 Channel Access Token |
   | `RELAY_SERVER_URL` | 上一步的 ngrok 網址，結尾不要斜線 |

3. 在編輯器執行 `checkConfig`，確認顯示「LINE token：已設定」。
4. **部署 → 新增部署作業 → 網頁應用程式**：
   - 執行身分：**我**
   - 存取權：**任何人**
5. 複製「網頁應用程式」的正式部署網址，貼到 LINE Developers → Messaging API → **Webhook URL**。
6. 點 **Verify**，並把 **Use webhook** 設為 **Enabled**。

> 如果 Verify 出現 302 或 403：通常是貼到測試用的開發網址，或部署的存取權不是「任何人」。

#### 4. Google Sheet 待辦

不需要手動建立試算表。第一次收到非「查」的訊息時，`Code.gs` 會自動建立「LINE Bot 待辦清單」，並把試算表 ID 記在指令碼屬性 `SPREADSHEET_ID`。

---

## 測試

### 單元測試（不需要 LINE token 或 Ollama）

```powershell
python -m unittest discover -s tests -v
```

目前 11 個測試，涵蓋：

- `clean_query` 是否正確移除「查／查詢／請問」等口語前綴。
- 新聞類問題是否優先走 Google News，知識類是否優先走 Wikipedia。
- 回答是否附上「來源：」，沒有搜尋結果時是否能正常回覆。
- `/ask` 在沒有 `replyToken` 時是否同步回 JSON。
- `/demo/message` 的查詢／待辦分流與空訊息檢查。
- `/health` 是否意外洩漏 token。

### 本機實測（Windows 11、Python 3.13、CPU 推論）

| 情境 | 搜尋 | 模型生成 | 總耗時 |
|---|---:|---:|---:|
| 冷啟動（模型尚未載入） | — | 14.0 秒 | **16.2 秒** |
| 暖機後查詢 | 2.2 秒 | 3.3 秒 | **5.5 秒** |
| 展示頁回歸測試 | — | — | **5.9 秒** |

> 冷啟動的 16.2 秒主要花在載入模型，不是完整查詢的代表值。這是 2026-10-31 在開發機上的單次觀測，不是嚴謹 benchmark；網路與硬體不同會有明顯差異。

### 手動 End-to-End 檢查清單

- [ ] `ollama list` 看得到 `gemma2:2b`。
- [ ] 轉接站首頁顯示「轉接站運行中！」。
- [ ] 展示頁問「查 玉山有多高」會在數秒內回覆，且看得到 Wikipedia 來源。
- [ ] LINE 傳「買牛奶」，Google Sheet 新增一列。
- [ ] LINE 傳「查 …」，回覆有答案與來源，而不是只有「已記錄」。
- [ ] 關掉轉接站時，LINE 端有錯誤提示，不會永久轉圈。

### 交件前安全檢查

```powershell
python scripts/check_submission.py
```

它會掃描 git 追蹤的檔案，檢查是否有 LINE／Gemini／ngrok 金鑰、Bearer token 或 Apps Script 正式部署網址。

---

## 安全與隱私

- **不要把 token 寫進 repo**。本機用環境變數；Apps Script 用「指令碼屬性」。
- `.gitignore` 已排除 `.env`、`Code_filled.gs`、`start_local.bat`、`todo.txt` 等本機檔案。
- 如果 token 曾經出現在對話、截圖或 commit，請立刻到 LINE Developers **重新發行 token**，舊 token 直接失效。
- 報告、投影片、截圖上傳前，請再人工檢查一次網址列、終端機與程式碼畫面。
- 這個架構不是「全部離線」：問題會經過 LINE、Google Apps Script 與公開搜尋服務；只有**模型推論**在本機。若資料敏感，請不要傳給 Bot。

---

## 已知限制

1. **電腦要開著**：關機、休眠或 Ollama 沒開，LINE 就查不到。
2. **ngrok 免費網址會變**：每次重開都要更新 Apps Script 的 `RELAY_SERVER_URL`。
3. **搜索結果很淺**：Google News RSS 只給標題與媒體首頁，Wikipedia 只給摘要；答案可能不夠新或不够深。
4. **2B 模型會出錯**：已用 prompt 限制「只根據搜尋結果回答」，但仍可能誤解或漏答。
5. **尚未驗證 LINE 簽章**：目前 Apps Script 直接接收 Webhook；公開部署後，任何人知道網址都能送假事件。下一步應驗證 `X-Line-Signature` 或加上來源限制。
6. **Google Sheet 會存使用者 ID**：多人使用時要考慮保留期限與存取權限。

---

## 下一步

- 把 ngrok 換成 **Cloudflare Tunnel + 固定網域**，讓 Webhook 不用每次重設。
- 在 Apps Script 加入 **LINE 簽章驗證**與簡單的 allowlist。
- 待辦加上「列表／完成／刪除／截止日」，或直接串 Google Tasks。
- 搜尋改成「先抓文章正文，再切 chunk 做 RAG」，而不是只餵 RSS 摘要。
- 加上 GPU 或雲端小模型 fallback，讓電腦關機時仍可回答。
- 把回覆做成 LINE Flex Message，來源用按鈕而不是長網址。

---

## 檔案說明

| 檔案 | 說明 |
|---|---|
| `Code.gs` | Google Apps Script Webhook：讀指令碼屬性、分流、非同步轉接、寫 Google Sheet |
| `relay_server.py` | Flask 轉接站：搜尋、Ollama 回答、附來源、LINE Reply、展示頁 |
| `templates/demo.html` | 課堂展示頁（手機版聊天 UI＋流程面板） |
| `static/demo.css`、`static/demo.js` | 展示頁樣式與互動 |
| `line_bot_local.py` | 早期版本：不用 Apps Script，直接在本機當 Webhook（備份參考） |
| `cloudflare_worker.js` | 另一種雲端版本：改用 Gemini API，不需本機 Ollama（備份參考） |
| `google_apps_script.gs` | 早期 Gemini + Apps Script 版本（備份參考） |
| `tests/test_relay.py` | 不需外部服務的單元測試 |
| `scripts/check_submission.py` | 交件前的敏感資料掃描 |
| `scripts/generate_assets.py` | 產生報告用架構圖 |
| `docs/` | 專題報告、AI 對話摘要、投影片、90 秒腳本與截圖 |
| `requirements.txt` | Python 依賴套件 |

---

## 開發過程

這個專案是與 AI 編程助理一起迭代完成的：先做 Cloudflare Worker + Gemini 版本，發現需要 API key 與額度；再改成 Apps Script + 本機 Ollama，最後處理 LINE 逾時、搜尋來源不穩、ngrok 網址、UTF-8 亂碼與 token 外洩風險。完整的除錯紀錄與 prompt 整理在 [`docs/AI對話摘要.md`](docs/AI對話摘要.md)。
