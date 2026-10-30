/**
 * LINE Bot - Google Apps Script Webhook
 *
 * 收到「查 ...」→ 轉給本機轉接站（Ollama）回答
 * 收到「咖啡 45 元」→ 本機記帳，回今日／本月累計
 * 其他訊息 → 記錄到 Google Sheet 待辦
 *
 * 設定方式（不要把 token 貼進程式碼）：
 * 1. 到 Apps Script → 專案設定 → 指令碼屬性，新增：
 *      LINE_CHANNEL_ACCESS_TOKEN = 你的 token
 *      RELAY_SERVER_URL         = 轉接站公開網址（結尾不要斜線）
 * 2. 部署 → 新增部署作業 → 網頁應用程式
 *    執行身分：我　存取權：任何人
 * 3. 把正式部署網址貼到 LINE Developers 的 Webhook URL
 */

// ===== 設定 =====
const SHEET_NAME = "LINE Bot 待辦";

function getConfig_() {
  const props = PropertiesService.getScriptProperties();
  const token = (props.getProperty("LINE_CHANNEL_ACCESS_TOKEN") || "").trim();
  const relay = (props.getProperty("RELAY_SERVER_URL") || "").trim().replace(/\/+$/, "");

  if (!token || !relay) {
    throw new Error("請先在「專案設定 → 指令碼屬性」設定 LINE_CHANNEL_ACCESS_TOKEN 與 RELAY_SERVER_URL");
  }
  return { token: token, relay: relay };
}

// 在編輯器手動執行這個函式，可以確認設定是否讀得到（不會印出 token）
function checkConfig() {
  const config = getConfig_();
  console.log("轉接站：" + config.relay);
  console.log("LINE token：已設定");
  return "OK";
}

// ===== LINE Webhook =====
function doPost(e) {
  if (!e || !e.postData || !e.postData.contents) {
    return ContentService.createTextOutput("OK");
  }

  let body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (err) {
    console.error("Webhook JSON 解析失敗：" + err.message);
    return ContentService.createTextOutput("OK");
  }

  const events = body.events || [];

  for (const event of events) {
    if (event.type === "message" && event.message.type === "text") {
      const userText = event.message.text;
      const userId = event.source.userId;

      let replyText = "";
      let handledByRelay = false;

      // 判斷是否要交給本地轉接站：
      // - 「查 …」→ 搜尋 + Ollama 回答
      // - 「咖啡 45 元」→ 本地記帳，回今日／本月累計
      const isExpenseText = /^(買|花|支出|購買)?\s*.+?\s+\d/.test(userText);

      if (userText.startsWith("查") || isExpenseText) {
        // 轉給本地轉接站（Ollama / 記帳）；轉接站算完會直接回 LINE
        askRelay(userText, event.replyToken);
        handledByRelay = true;
      } else {
        // 記錄到 Google Sheet 待辦
        addToTodo(userId, userText);
        replyText = "已記錄到待辦：" + userText;
      }

      // 回覆使用者（「查 …」由轉接站回，這裡不重複回）
      if (!handledByRelay) {
        replyLINE(event.replyToken, replyText);
      }
    }
  }

  return ContentService.createTextOutput("OK");
}

// ===== 轉給本地轉接站 =====
function askRelay(question, replyToken) {
  try {
    const config = getConfig_();
    const options = {
      method: "POST",
      contentType: "application/json",
      payload: JSON.stringify({ question: question, replyToken: replyToken }),
      headers: { "ngrok-skip-browser-warning": "true" },
      muteHttpExceptions: true
    };

    // 轉接站會立刻回 202，實際答案由轉接站直接回 LINE
    UrlFetchApp.fetch(config.relay + "/ask", options);
  } catch (err) {
    // 轉接站連不上時，至少讓使用者知道
    replyLINE(replyToken, "轉接站連不上：" + err.message);
  }
}

// ===== 回覆 LINE =====
function replyLINE(replyToken, text) {
  try {
    const config = getConfig_();
    const options = {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + config.token,
        "Content-Type": "application/json"
      },
      payload: JSON.stringify({
        replyToken: replyToken,
        messages: [{
          type: "text",
          text: text
        }]
      }),
      muteHttpExceptions: true
    };

    UrlFetchApp.fetch("https://api.line.me/v2/bot/message/reply", options);
  } catch (err) {
    console.error("回覆 LINE 失敗：" + err.message);
  }
}

// ===== 記錄到 Google Sheet 待辦 =====
function getTodoSheet() {
  const props = PropertiesService.getScriptProperties();
  let ss = null;

  // 1. 先找之前建立過的試算表
  const savedId = props.getProperty("SPREADSHEET_ID");
  if (savedId) {
    try { ss = SpreadsheetApp.openById(savedId); } catch (err) { ss = null; }
  }

  // 2. 再試「綁定的試算表」
  if (!ss) {
    try { ss = SpreadsheetApp.getActiveSpreadsheet(); } catch (err) { ss = null; }
  }

  // 3. 都沒有就自動建一份，並記住 ID
  if (!ss) {
    ss = SpreadsheetApp.create("LINE Bot 待辦清單");
    props.setProperty("SPREADSHEET_ID", ss.getId());
  }

  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(["時間", "使用者ID", "待辦事項"]);
  }
  return sheet;
}

function addToTodo(userId, text) {
  try {
    getTodoSheet().appendRow([
      new Date().toLocaleString("zh-TW"),
      userId,
      text
    ]);
  } catch (err) {
    console.error("記錄失敗：" + err.message);
  }
}

// ===== GET 請求也回 OK（避免 302） =====
function doGet() {
  return ContentService.createTextOutput("OK").setMimeType(ContentService.MimeType.TEXT);
}
