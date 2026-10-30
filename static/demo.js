(() => {
  const chat = document.getElementById("chat");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("message");
  const chips = document.getElementById("chips");
  const latency = document.getElementById("latency");
  const todoList = document.getElementById("todos");
  const todoCount = document.getElementById("todoCount");
  const stepEls = [...document.querySelectorAll("#steps li")];
  const sendButton = form.querySelector("button");

  let busy = false;
  let timers = [];

  const now = () => {
    const d = new Date();
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  };

  function scrollDown() {
    requestAnimationFrame(() => {
      chat.scrollTop = chat.scrollHeight;
    });
  }

  function addMessage(role, content, time = now()) {
    const msg = document.createElement("div");
    msg.className = `msg ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "bubble";

    if (typeof content === "string") {
      bubble.textContent = content;
      bubble.style.whiteSpace = "pre-wrap";
    } else {
      bubble.appendChild(content);
    }

    const stamp = document.createElement("time");
    stamp.textContent = time;
    msg.append(bubble, stamp);
    chat.appendChild(msg);
    scrollDown();
    return msg;
  }

  function linkify(text) {
    const frag = document.createDocumentFragment();
    const urlRe = /https?:\/\/[^\s<>"']+/g;
    let last = 0;
    let m;
    while ((m = urlRe.exec(text)) !== null) {
      if (m.index > last) frag.append(text.slice(last, m.index));
      const a = document.createElement("a");
      a.href = m[0];
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = m[0].length > 56 ? m[0].slice(0, 53) + "…" : m[0];
      frag.append(a);
      last = m.index + m[0].length;
    }
    if (last < text.length) frag.append(text.slice(last));
    return frag;
  }

  function answerContent(text) {
    const wrap = document.createElement("div");
    const marker = text.lastIndexOf("\n\n來源：");
    const body = marker >= 0 ? text.slice(0, marker) : text;
    const sources = marker >= 0 ? text.slice(marker + 5).trim() : "";
    wrap.append(linkify(body));

    if (sources) {
      const block = document.createElement("div");
      block.className = "source-block";
      const title = document.createElement("b");
      title.textContent = "來源";
      block.append(title);

      const items = sources.split(/\n(?=\d+\.\s)/);
      items.forEach((item) => {
        const lines = item.split("\n").map((line) => line.trim()).filter(Boolean);
        if (!lines.length) return;
        const label = lines[0].replace(/^\d+\.\s*/, "");
        const url = lines.find((line) => /^https?:\/\//.test(line));
        const row = document.createElement(url ? "a" : "div");
        row.className = "source-item";
        const name = document.createElement("span");
        name.textContent = label;
        row.append(name);
        if (url) {
          row.href = url;
          row.target = "_blank";
          row.rel = "noopener noreferrer";
          const host = document.createElement("small");
          try {
            host.textContent = new URL(url).hostname.replace(/^www\./, "");
          } catch {
            host.textContent = url;
          }
          row.append(host);
        }
        block.append(row);
      });
      wrap.append(block);
    }
    wrap.style.whiteSpace = "pre-wrap";
    return wrap;
  }

  function addTyping() {
    const wrap = document.createElement("div");
    wrap.className = "typing";
    wrap.innerHTML = "<i></i><i></i><i></i>";
    return addMessage("bot", wrap);
  }

  function resetSteps() {
    timers.forEach(clearTimeout);
    timers = [];
    stepEls.forEach((el) => {
      el.classList.remove("active", "done");
      el.querySelector(".state").textContent = "待機";
    });
    latency.textContent = "—";
  }

  function setStep(n, state) {
    const el = stepEls.find((x) => Number(x.dataset.step) === n);
    if (!el) return;
    el.classList.toggle("active", state === "active");
    el.classList.toggle("done", state === "done");
    el.querySelector(".state").textContent = state === "active" ? "進行中" : state === "done" ? "完成" : "待機";
  }

  function startPipeline(kind) {
    resetSteps();
    setStep(1, "done");
    if (kind === "answer") {
      timers.push(setTimeout(() => setStep(2, "active"), 250));
      timers.push(setTimeout(() => { setStep(2, "done"); setStep(3, "active"); }, 1800));
      timers.push(setTimeout(() => { setStep(3, "done"); setStep(4, "active"); }, 4200));
    } else {
      setStep(4, "active");
    }
  }

  function finishPipeline() {
    timers.forEach(clearTimeout);
    timers = [];
    stepEls.forEach((el) => {
      el.classList.remove("active");
      el.classList.add("done");
      el.querySelector(".state").textContent = "完成";
    });
  }

  async function refreshTodos() {
    try {
      const res = await fetch("/demo/todos");
      const data = await res.json();
      const todos = data.todos || [];
      todoCount.textContent = String(todos.length);
      todoList.innerHTML = "";
      if (!todos.length) {
        const li = document.createElement("li");
        li.className = "empty";
        li.textContent = "還沒有待辦，傳一句「買牛奶」試試。";
        todoList.append(li);
        return;
      }
      todos.forEach((todo) => {
        const li = document.createElement("li");
        const text = document.createElement("span");
        text.textContent = todo.text;
        const time = document.createElement("span");
        time.className = "t-time";
        time.textContent = todo.time.slice(5, 16);
        li.append(text, time);
        todoList.append(li);
      });
    } catch {
      /* 展示頁讀不到待辦時不影響聊天 */
    }
  }

  async function sendMessage(raw) {
    const text = (raw || "").trim();
    if (!text || busy) return;

    busy = true;
    sendButton.disabled = true;
    input.value = "";
    addMessage("user", text);

    const kind = text.startsWith("查") ? "answer" : "todo";
    startPipeline(kind);
    const typing = addTyping();

    try {
      const res = await fetch("/demo/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, kind }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "伺服器沒有回應");

      typing.remove();
      if (data.kind === "answer") {
        addMessage("bot", answerContent(data.answer || ""));
      } else {
        addMessage("bot", data.message || "已記錄。");
        refreshTodos();
      }
      latency.textContent = `${data.elapsed ?? "?"} 秒`;
      finishPipeline();
    } catch (err) {
      typing.remove();
      addMessage("bot", `連線失敗：${err.message}\n請確認 Ollama 與展示伺服器正在執行。`);
      latency.textContent = "—";
      resetSteps();
    } finally {
      busy = false;
      sendButton.disabled = false;
      input.focus();
      scrollDown();
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage(input.value);
  });

  chips.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-text]");
    if (!button) return;
    sendMessage(button.dataset.text);
  });

  refreshTodos();
})();
