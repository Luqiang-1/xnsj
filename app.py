import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from config import HOST, PORT, STATIC_DIR
from knowledge_graph import graph_service
from rag_engine import engine


class RAGRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"status": "ok", "chunks": len(engine.chunks)})
            return
        if parsed.path == "/api/knowledge/overview":
            self._send_json(graph_service.overview(chunk_count=len(engine.chunks)))
            return
        if parsed.path == "/api/knowledge/crop":
            crop_name = parse_qs(parsed.query).get("name", [""])[0].strip()
            if not crop_name:
                self._send_json({"error": "Missing crop name"}, status=400)
                return
            detail = graph_service.crop_detail(crop_name)
            if detail is None:
                self._send_json({"error": "Crop not found"}, status=404)
                return
            self._send_json(detail)
            return
        if parsed.path == "/api/reload":
            engine.reload()
            graph_service.reload()
            self._send_json({"status": "reloaded", "chunks": len(engine.chunks)})
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/ask":
            self.send_error(404, "Not Found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body or "{}")
            question = str(data.get("question", "")).strip()
        except (ValueError, json.JSONDecodeError):
            self.send_error(400, "Invalid JSON")
            return

        if not question:
            self._send_json({"answer": "请输入问题。", "sources": [], "contexts": []}, status=400)
            return

        self._send_json(engine.answer(question))

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), RAGRequestHandler)
    print(f"果用经济作物知识库问答系统已启动: http://{HOST}:{PORT}")
    print("按 Ctrl+C 停止服务。")
    server.serve_forever()


if __name__ == "__main__":
    main()
