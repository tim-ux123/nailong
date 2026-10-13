# -*- coding: utf-8 -*-
"""
美食智能体 Web 服务
运行: python server.py  ->  浏览器打开 http://localhost:8000
复用 food_agent.solve 的 ReAct 推理逻辑, 通过 /api/chat 提供接口。
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import food_agent

PORT = 8000
BASE = os.path.dirname(os.path.abspath(__file__))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(os.path.join(BASE, "index.html"), "r", encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "index.html not found", "text/plain; charset=utf-8")
        elif self.path == "/api/health":
            self._send(200, json.dumps({"model": food_agent.MODEL, "status": "ok"}))
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/chat":
            self._send(404, "not found", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length).decode("utf-8"))
            question = (req.get("message") or "").strip()
            if not question:
                self._send(400, json.dumps({"error": "消息不能为空"}))
                return
            answer, trace = food_agent.solve(question, verbose=False, with_trace=True)
            self._send(200, json.dumps({"reply": answer, "trace": trace}, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))

    def log_message(self, *args):
        pass  # 静默, 保持终端干净


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("=" * 46)
    print("  美食智能体 Web 服务已启动")
    print(f"  请用浏览器打开:  http://localhost:{PORT}")
    print("  确保 Ollama 正在运行, 按 Ctrl+C 停止服务")
    print("=" * 46)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
