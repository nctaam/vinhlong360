/* vinhlong360 — Chat Widget (kết nối Knowledge Agent) */

(function () {
  const AGENT_URL = "http://localhost:8360";
  const panel = document.getElementById("chatPanel");
  const fab = document.getElementById("chatFab");
  const msgsEl = document.getElementById("chatMsgs");
  const inputEl = document.getElementById("chatInput");
  const sendBtn = document.getElementById("chatSendBtn");
  let history = [];

  window.toggleChat = function () {
    const open = panel.classList.toggle("show");
    fab.classList.toggle("open", open);
    fab.textContent = open ? "✕" : "💬";
    if (open) inputEl.focus();
  };

  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !sendBtn.disabled) chatSend();
  });

  window.chatAsk = function (text) {
    inputEl.value = text;
    chatSend();
  };

  window.chatSend = async function () {
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = "";

    addMsg("user", text);
    history.push({ role: "user", content: text });
    sendBtn.disabled = true;

    const typing = document.createElement("div");
    typing.className = "c-typing";
    typing.innerHTML = "<span></span><span></span><span></span>";
    msgsEl.appendChild(typing);
    msgsEl.scrollTop = msgsEl.scrollHeight;

    try {
      const params = new URLSearchParams({
        message: text,
        history: JSON.stringify(history.slice(-20)),
      });
      const response = await fetch(AGENT_URL + "/chat/stream?" + params);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      typing.remove();
      const msgDiv = addMsg("assistant", "", true);
      let fullText = "";
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "text") {
              fullText += data.content;
              msgDiv.innerHTML = renderMd(fullText);
              msgsEl.scrollTop = msgsEl.scrollHeight;
            } else if (data.type === "done") {
              if (data.suggestions && data.suggestions.length) showSuggestions(data.suggestions);
              showFeedback(msgDiv, text);
            }
          } catch (_) {}
        }
      }

      history.push({ role: "assistant", content: fullText });
    } catch (err) {
      typing.remove();
      addMsg("assistant", "Không kết nối được Agent. Hãy chạy: python agent/server.py");
    }
    sendBtn.disabled = false;
    inputEl.focus();
  };

  function addMsg(role, content, isHtml) {
    const div = document.createElement("div");
    div.className = "cmsg " + role;
    if (isHtml) div.innerHTML = content || "";
    else div.textContent = content;
    msgsEl.appendChild(div);
    msgsEl.scrollTop = msgsEl.scrollHeight;
    return div;
  }

  function showSuggestions(items) {
    const old = msgsEl.querySelector(".csuggestions:last-child");
    if (old) old.remove();
    const div = document.createElement("div");
    div.className = "csuggestions";
    items.forEach(function (text) {
      const btn = document.createElement("button");
      btn.textContent = text;
      btn.onclick = function () {
        div.remove();
        chatAsk(text);
      };
      div.appendChild(btn);
    });
    msgsEl.appendChild(div);
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function showFeedback(msgDiv, query) {
    var row = document.createElement("div");
    row.className = "csuggestions";
    var up = document.createElement("button");
    up.textContent = "👍";
    var down = document.createElement("button");
    down.textContent = "👎";
    up.onclick = function () {
      sendFeedback(query, 1);
      down.style.display = "none";
      up.disabled = true;
    };
    down.onclick = function () {
      sendFeedback(query, 0);
      up.style.display = "none";
      down.disabled = true;
    };
    row.appendChild(up);
    row.appendChild(down);
    msgDiv.appendChild(row);
  }

  function sendFeedback(query, rating) {
    fetch(AGENT_URL + "/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, rating: rating, session_id: "web-widget" }),
    }).catch(function () {});
  }

  function renderMd(text) {
    var html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/`(.+?)`/g, "<code>$1</code>")
      .replace(/^### (.+)$/gm, "<strong>$1</strong><br>")
      .replace(/^## (.+)$/gm, "<strong>$1</strong><br>")
      .replace(/^# (.+)$/gm, "<strong>$1</strong><br>");

    html = html.replace(/^[\-\*] (.+)$/gm, "<li>$1</li>");
    html = html.replace(/^(\d+)\. (.+)$/gm, "<li>$2</li>");
    html = html.replace(/(<li>.*<\/li>)/gs, function (m) {
      return "<ul>" + m + "</ul>";
    });
    html = html.replace(/<\/ul>\s*<ul>/g, "");

    html = html.replace(/\n\n/g, "</p><p>");
    html = "<p>" + html + "</p>";
    html = html.replace(/<p><\/p>/g, "");

    return html;
  }
})();
