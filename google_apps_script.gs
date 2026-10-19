/**
 * LINE Bot + Google Gemini API + Google Sheet 記錄
 * 
 * 部署方式：
 * 1. 前往 https://script.google.com/ 建立新專案
 * 2. 把這段程式碼貼上
 * 3. 部署 → Web app → 設定執行身分為「我」，存取權為「任何人」
 * 4. 把部署後的 URL + /callback 貼到 LINE Developers 的 Webhook URL
 */

// ===== 設定 =====
const GEMINI_API_KEY = "你的_Gemini_API_Key"; // 從 https://aistudio.google.com/apikey 取得
const LINE_CHANNEL_ACCESS_TOKEN = "你的_LINE_CHANNEL_ACCESS_TOKEN";
const SHEET_NAME = "LINE Bot 記錄";

// ===== LINE Webhook =====
function doPost(e) {
  const body = JSON.parse(e.postData.contents);
  const events = body.events;
  
  for (const event of events) {
    if (event.type === "message" && event.message.type === "text") {
      const userText = event.message.text;
      const userId = event.source.userId;
      
      // 用 Gemini API 回答
      const replyText = askGemini(userText);
      
      // 記錄到 Google Sheet
      logToSheet(userId, userText, replyText);
      
      // 回覆使用者
      replyLINE(event.replyToken, replyText);
    }
  }
  
  return ContentService.createTextOutput("OK");
}

// ===== Gemini API =====
function askGemini(question) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`;
  
  const payload = {
    contents: [{
      parts: [{
        text: `你是一個有幫助的助手。請用繁體中文回答以下問題：\n\n${question}`
      }]
    }]
  };
  
  const options = {
    method: "POST",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  
  try {
    const response = UrlFetchApp.fetch(url, options);
    const result = JSON.parse(response.getContentText());
    return result.candidates[0].content.parts[0].text;
  } catch (e) {
    return "抱歉，發生錯誤：" + e.message;
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

// ===== 記錄到 Google Sheet =====
function logToSheet(userId, question, answer) {
  try {
    let ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(SHEET_NAME);
    
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_NAME);
      sheet.appendRow(["時間", "使用者ID", "問題", "回答"]);
    }
    
    sheet.appendRow([
      new Date().toLocaleString("zh-TW"),
      userId,
      question,
      answer
    ]);
  } catch (e) {
    Console.log("記錄失敗：" + e.message);
  }
}

// ===== 測試用 =====
function doGet() {
  return ContentService.createTextOutput("LINE Bot + Gemini API is running!");
}
