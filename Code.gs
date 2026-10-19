/**
 * LINE Bot - Google Apps Script Webhook
 * 
 * 收到「查 ...」→ 轉給本地轉接站（Ollama）回答
 * 其他訊息 → 記錄到 Google Sheet 待辦
 * 
 * 部署方式：
 * 1. 前往 https://script.google.com/ 建立新專案
 * 2. 把這段程式碼貼上
 * 3. 設定部署為 Web App（執行身份：我，存取權：任何人）
 * 4. 部署後的 URL + /callback 貼到 LINE Developers 的 Webhook URL
 */

// ===== 設定 =====
const LINE_CHANNEL_ACCESS_TOKEN = "你的_LINE_CHANNEL_ACCESS_TOKEN";
const RELAY_SERVER_URL = "你的轉接站公開網址"; // 例如 https://xxxx.ngrok-free.app
const SHEET_NAME = "LINE Bot 待辦";

// ===== LINE Webhook =====
function doPost(e) {
  const body = JSON.parse(e.postData.contents);
  const events = body.events;
  
  for (const event of events) {
    if (event.type === "message" && event.message.type === "text") {
      const userText = event.message.text;
      const userId = event.source.userId;
      
      let replyText = "";
      
      // 判斷是否為「查 ...」
      if (userText.startsWith("查")) {
        // 轉給本地轉接站（Ollama）
        replyText = askRelay(userText);
      } else {
        // 記錄到 Google Sheet 待辦
        addToTodo(userId, userText);
        replyText = "已記錄到待辦：" + userText;
      }
      
      // 回覆使用者
      replyLINE(event.replyToken, replyText);
    }
  }
  
  return ContentService.createTextOutput("OK");
}

// ===== 轉給本地轉接站 =====
function askRelay(question) {
  try {
    const url = RELAY_SERVER_URL + "/ask";
    const options = {
      method: "POST",
      contentType: "application/json",
      payload: JSON.stringify({ question: question }),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(url, options);
    const result = JSON.parse(response.getContentText());
    return result.answer;
  } catch (e) {
    return "轉接站錯誤：" + e.message;
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
function addToTodo(userId, text) {
  try {
    let ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(SHEET_NAME);
    
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_NAME);
      sheet.appendRow(["時間", "使用者ID", "待辦事項"]);
    }
    
    sheet.appendRow([
      new Date().toLocaleString("zh-TW"),
      userId,
      text
    ]);
  } catch (e) {
    Console.log("記錄失敗：" + e.message);
  }
}

// ===== 測試用 =====
function doGet() {
  return ContentService.createTextOutput("LINE Bot Webhook is running!");
}
