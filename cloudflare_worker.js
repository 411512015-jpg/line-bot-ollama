/**
 * LINE Bot + Gemini API - Cloudflare Worker 版
 * 
 * 部署方式：
 * 1. 前往 https://workers.cloudflare.com/ 註冊免費帳號
 * 2. 建立一個新的 Worker
 * 3. 把這段程式碼貼上
 * 4. 設定環境變數（Settings → Variables）：
 *    - LINE_CHANNEL_ACCESS_TOKEN
 *    - GEMINI_API_KEY
 * 5. 部署後得到一個公開網址
 * 6. 把網址 + /callback 貼到 LINE Developers 的 Webhook URL
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    
    // Webhook endpoint
    if (url.pathname === "/callback" && request.method === "POST") {
      const body = await request.json();
      const events = body.events;
      
      for (const event of events) {
        if (event.type === "message" && event.message.type === "text") {
          const userText = event.message.text;
          const userId = event.source.userId;
          
          // 用 Gemini API 回答
          const replyText = await askGemini(userText, env.GEMINI_API_KEY);
          
          // 回覆使用者
          await replyLINE(event.replyToken, replyText, env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      
      return new Response("OK", { status: 200 });
    }
    
    // 測試用
    return new Response("LINE Bot + Gemini API is running!", { status: 200 });
  }
};

// ===== Gemini API =====
async function askGemini(question, apiKey) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;
  
  const payload = {
    contents: [{
      parts: [{
        text: `你是一個有幫助的助手。請用繁體中文回答以下問題：\n\n${question}`
      }]
    }]
  };
  
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    const result = await response.json();
    return result.candidates[0].content.parts[0].text;
  } catch (e) {
    return "抱歉，發生錯誤：" + e.message;
  }
}

// ===== 回覆 LINE =====
async function replyLINE(replyToken, text, accessToken) {
  const url = "https://api.line.me/v2/bot/message/reply";
  
  await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": "Bearer " + accessToken,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      replyToken: replyToken,
      messages: [{
        type: "text",
        text: text
      }]
    })
  });
}
