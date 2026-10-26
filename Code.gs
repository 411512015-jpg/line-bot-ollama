/**
 * LINE Bot - Google Apps Script Webhook
 * 
 * 收到「查 ...」→ 轉給本地轉接站（Ollama）回答
 * 其他訊息 → 記錄到 Google Sheet 待辦
 * 
 * 部署方式：
 * 1. 前往 https://script.google.com/ 建立新專案
 * 2. 把這段程式碼貼上，並填好下面的 token 與轉接站網址
 * 3. 部署 → 新增部署作業 → 網頁應用程式
 *    執行身分：我　存取權：任何人
 * 4. 把「部署網址」（結尾是 /exec，不是 /dev）整串貼到 LINE 的 Webhook URL
 */

// ===== 設定 =====
const LINE_CHANNEL_ACCESS_TOKEN = "你的_LINE_CHANNEL_ACCESS_TOKEN";
const RELAY_SERVER_URL = "你的轉接站公開網址"; // 例如 https://xxxx.ngrok-free.app
const SHEET_NAME = "LINE Bot 待辦";

// ===== LINE Webhook =====
function doPost(e) {
  if (!e || !e.postData || !e.postData.contents) {
    return ContentService.createTextOutput("OK");
  }
  const body = JSON.parse(e.postData.contents);
  const events = body.events;
  
  for (const event of events) {
    if (event.type === "message" && event.message.type === "text") {
      const userText = event.message.text;
      const userId = event.source.userId;
      
      let replyText = "";
      let handledByRelay = false;
      
      // 判斷是否為「查 ...」
      if (userText.startsWith("查")) {
        // 轉給本地轉接站（Ollama）；轉接站算完會直接回 LINE
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
    const url = RELAY_SERVER_URL + "/ask";
    const options = {
      method: "POST",
      contentType: "application/json",
      payload: JSON.stringify({ question: question, replyToken: replyToken }),
      headers: { "ngrok-skip-browser-warning": "true" },
      muteHttpExceptions: true
    };

    // 轉接站會立刻回 202，實際答案由轉接站直接回 LINE
    UrlFetchApp.fetch(url, options);
  } catch (e) {
    // 轉接站連不上時，至少讓使用者知道
    replyLINE(replyToken, "轉接站連不上：" + e.message);
  }
}

// ===== 回覆 LINE =====
function replyLINE(replyToken, text) {
  const url = "https://api.line.me/v2/bot/message/reply";
  
  const options = {
    method: "POST",
    headers: {
      "Authorization": "Bearer " + LINE_CHANNEL_ACCESS_TOKEN,
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
  
  UrlFetchApp.fetch(url, options);
}

// ===== 記錄到 Google Sheet 待辦 =====
function getTodoSheet() {
  const props = PropertiesService.getScriptProperties();
  let ss = null;

  // 1. 先找之前建立過的試算表
  const savedId = props.getProperty("SPREADSHEET_ID");
  if (savedId) {
    try { ss = SpreadsheetApp.openById(savedId); } catch (e) { ss = null; }
  }

  // 2. 再試「綁定的試算表」
  if (!ss) {
    try { ss = SpreadsheetApp.getActiveSpreadsheet(); } catch (e) { ss = null; }
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
  } catch (e) {
    console.log("記錄失敗：" + e.message);
  }
}

// ===== GET 請求也回 OK（避免 302） =====
function doGet() {
  return ContentService.createTextOutput("OK").setMimeType(ContentService.MimeType.TEXT);
}
