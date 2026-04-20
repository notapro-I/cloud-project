from __future__ import annotations

import json
import os
import sys
import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
SDK_SRC_DIR = ROOT_DIR / "sdk" / "src"
if str(SDK_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SDK_SRC_DIR))

from llmobs.client import LLMObserver

HOST = "127.0.0.1"
PORT = 7860
DEFAULT_OLLAMA_BASE_URL = os.getenv("LLMOBS_OLLAMA_BASE_URL", "http://10.81.34.74:11434")

API_BASE_URL = os.getenv("LLMOBS_API_BASE_URL", "http://localhost:8000")


def normalize_ollama_base_url(url: str) -> str:
    normalized = url.strip().rstrip("/")
    if normalized.endswith("/api/generate"):
        normalized = normalized[: -len("/api/generate")]
    return normalized

HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LLM Chat (SDK)</title>
  <style>
    :root {
      --bg: #f4efe8;
      --panel: #fffaf2;
      --ink: #1f1b16;
      --muted: #6d6358;
      --brand: #b64d2f;
      --brand-dark: #8c3219;
      --line: #e8dac8;
      --assistant: #f6e7d6;
      --user: #fef3d7;
      --shadow: 0 12px 34px rgba(74, 49, 29, 0.12);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: "Georgia", "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 10% 15%, #fef3d7 0%, transparent 25%),
        radial-gradient(circle at 85% 10%, #f1dcc4 0%, transparent 30%),
        linear-gradient(160deg, #f7efe4 0%, #efe5d8 45%, #f8f1e6 100%);
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 20px;
    }

    .app {
      width: min(920px, 100%);
      height: min(92vh, 860px);
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: var(--shadow);
      display: grid;
      grid-template-rows: auto 1fr auto;
      overflow: hidden;
    }

    .topbar {
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(90deg, #fff7ea, #fff3e2);
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
    }

    .title {
      font-size: clamp(18px, 2.4vw, 24px);
      letter-spacing: 0.3px;
      margin: 0;
    }

    .controls {
      display: flex;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 14px;
      flex-wrap: wrap;
    }

    select,
    input[type="text"] {
      border: 1px solid var(--line);
      background: white;
      color: var(--ink);
      border-radius: 10px;
      padding: 8px 10px;
      font: inherit;
    }

    input[type="text"] {
      min-width: min(360px, 80vw);
    }

    #messages {
      overflow-y: auto;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .msg {
      max-width: min(80ch, 90%);
      padding: 12px 14px;
      border-radius: 14px;
      line-height: 1.45;
      border: 1px solid var(--line);
      white-space: pre-wrap;
      word-break: break-word;
      animation: rise 220ms ease;
    }

    .assistant {
      background: var(--assistant);
      align-self: flex-start;
    }

    .user {
      background: var(--user);
      align-self: flex-end;
    }

    .composer {
      border-top: 1px solid var(--line);
      padding: 12px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      background: #fff9f0;
    }

    textarea {
      width: 100%;
      resize: vertical;
      min-height: 56px;
      max-height: 180px;
      border: 1px solid #ddc7ad;
      border-radius: 12px;
      padding: 10px 12px;
      font: inherit;
      color: var(--ink);
      background: white;
    }

    button {
      align-self: end;
      border: none;
      border-radius: 12px;
      padding: 11px 14px;
      color: #fff;
      font: inherit;
      font-weight: 600;
      background: linear-gradient(180deg, var(--brand), var(--brand-dark));
      cursor: pointer;
      min-width: 96px;
    }

    button:disabled {
      opacity: 0.65;
      cursor: not-allowed;
    }

    .hint {
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      padding: 0 14px 10px;
    }

    @keyframes rise {
      from { transform: translateY(6px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    @media (max-width: 680px) {
      .app { height: 96vh; border-radius: 14px; }
      .composer { grid-template-columns: 1fr; }
      button { width: 100%; }
      .msg { max-width: 100%; }
    }
  </style>
</head>
<body>
  <main class="app">
    <header class="topbar">
      <h1 class="title">LLM Chat (with llmobs SDK)</h1>
      <div class="controls">
        <label for="model">Model</label>
        <select id="model">
          <option value="llama3.1" selected>llama3.1</option>
          <option value="llama3">llama3</option>
          <option value="mistral">mistral</option>
        </select>
        <label for="ollamaUrl">Ollama URL</label>
        <input id="ollamaUrl" type="text" value="__DEFAULT_OLLAMA_BASE_URL__" placeholder="http://host:11434" />
      </div>
    </header>

    <section id="messages"></section>

    <form id="chatForm" class="composer">
      <textarea id="prompt" placeholder="Ask anything..." required></textarea>
      <button id="sendBtn" type="submit">Send</button>
    </form>
    <p class="hint">Enter sends. Shift+Enter adds a new line.</p>
  </main>

  <script>
    const messagesEl = document.getElementById("messages");
    const formEl = document.getElementById("chatForm");
    const promptEl = document.getElementById("prompt");
    const sendBtnEl = document.getElementById("sendBtn");
    const modelEl = document.getElementById("model");
    const ollamaUrlEl = document.getElementById("ollamaUrl");

    function addMessage(role, text) {
      const item = document.createElement("div");
      item.className = `msg ${role}`;
      item.textContent = text;
      messagesEl.appendChild(item);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    async function sendPrompt() {
      const prompt = promptEl.value.trim();
      if (!prompt) return;

      addMessage("user", prompt);
      promptEl.value = "";
      sendBtnEl.disabled = true;

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt,
            model: modelEl.value,
            ollama_base_url: ollamaUrlEl.value,
          }),
        });

        const data = await response.json();
        if (!response.ok) {
          addMessage("assistant", `Error: ${data.error || "request failed"}`);
          return;
        }

        addMessage("assistant", data.response || "(empty response)");
      } catch (error) {
        addMessage("assistant", `Network error: ${error.message}`);
      } finally {
        sendBtnEl.disabled = false;
        promptEl.focus();
      }
    }

    formEl.addEventListener("submit", async (event) => {
      event.preventDefault();
      await sendPrompt();
    });

    promptEl.addEventListener("keydown", async (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        await sendPrompt();
      }
    });

    addMessage("assistant", "Hello. Ask a question and I will reply via Ollama.");
    promptEl.focus();
  </script>
</body>
</html>
"""
HTML_PAGE = HTML_PAGE.replace("__DEFAULT_OLLAMA_BASE_URL__", html.escape(DEFAULT_OLLAMA_BASE_URL, quote=True))


class ChatHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send_html(HTML_PAGE)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self._send_json({"error": "Missing request body"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8"))
            prompt = str(payload.get("prompt", "")).strip()
            model = str(payload.get("model", "llama3.1")).strip() or "llama3.1"
            ollama_base_url = normalize_ollama_base_url(
                str(payload.get("ollama_base_url", DEFAULT_OLLAMA_BASE_URL))
            )
        except Exception:
            self._send_json({"error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            return

        if not prompt:
            self._send_json({"error": "Prompt is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        if not ollama_base_url:
            self._send_json({"error": "Ollama base URL is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        observer: LLMObserver | None = None
        try:
            observer = LLMObserver(api_base_url=API_BASE_URL, ollama_base_url=ollama_base_url)
            result = observer.call_ollama(model=model, prompt=prompt, prompt_template_id=None)
            response_text = str(result.get("response", ""))
            self._send_json({"response": response_text, "raw": result})
        except Exception as exc:
            self._send_json(
                {"error": f"Model call failed: {exc}"},
                status=HTTPStatus.BAD_GATEWAY,
            )
        finally:
            try:
                if observer is not None:
                    observer.close()
            except Exception:
                pass

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), ChatHandler)
    print(f"Chat app running at http://{HOST}:{PORT}")
    print(f"Default Ollama URL: {DEFAULT_OLLAMA_BASE_URL}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
