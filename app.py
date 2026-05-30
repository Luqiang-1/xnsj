from __future__ import annotations

import json
import re
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer
from urllib.parse import parse_qs, urlparse

from auth_store import AuthError, auth_store
from community_store import CommunityError, community_store
from config import AUTH_COOKIE_NAME, HOST, PORT, SESSION_MAX_AGE, STATIC_DIR
from knowledge_graph import graph_service
from rag_engine import engine


PROTECTED_PAGES = {
    "/system.html",
    "/knowledge-graph.html",
    "/community.html",
    "/crop-graph.html",
}
COMMUNITY_COMMENT_PATH = re.compile(r"^/api/community/posts/(?P<post_id>\d+)/comments$")


class LocalThreadingHTTPServer(ThreadingHTTPServer):
    def server_bind(self) -> None:
        TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = port


class RAGRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        username = self._current_user()

        if path == "/":
            self.path = "/index.html"
        elif path == "/auth.html" and username:
            self._redirect("/system.html")
            return
        elif path in PROTECTED_PAGES and not username:
            self._redirect("/auth.html")
            return

        super().do_HEAD()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        username = self._current_user()

        if path == "/":
            self.path = "/index.html"
            super().do_GET()
            return

        if path == "/auth.html" and username:
            self._redirect("/system.html")
            return

        if path in PROTECTED_PAGES and not username:
            self._redirect("/auth.html")
            return

        if path == "/api/health":
            self._send_json({"status": "ok", "chunks": len(engine.chunks)})
            return

        if path == "/api/auth/status":
            self._send_json(
                {
                    "authenticated": bool(username),
                    "username": username,
                }
            )
            return

        if path.startswith("/api/") and not username:
            self._send_json({"error": "请先登录。"}, status=401)
            return

        if path == "/api/knowledge/overview":
            self._send_json(graph_service.overview(chunk_count=len(engine.chunks)))
            return

        if path == "/api/knowledge/crop":
            crop_name = parse_qs(parsed.query).get("name", [""])[0].strip()
            if not crop_name:
                self._send_json({"error": "缺少作物名称。"}, status=400)
                return
            detail = graph_service.crop_detail(crop_name)
            if detail is None:
                self._send_json({"error": "未找到对应作物。"}, status=404)
                return
            self._send_json(detail)
            return

        if path == "/api/community/posts":
            self._send_json(
                {
                    "user": username,
                    "posts": community_store.list_posts(),
                    "stats": community_store.summary(),
                }
            )
            return

        if path == "/api/reload":
            engine.reload()
            graph_service.reload()
            self._send_json({"status": "reloaded", "chunks": len(engine.chunks)})
            return

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        username = self._current_user()

        if path == "/api/auth/register":
            payload = self._read_json_body()
            if payload is None:
                return
            try:
                registered_username = auth_store.register(
                    str(payload.get("username", "")),
                    str(payload.get("password", "")),
                )
                session_token = auth_store.create_session(registered_username)
            except AuthError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            self._send_json(
                {"message": "注册成功。", "username": registered_username},
                status=201,
                extra_headers=[("Set-Cookie", self._build_session_cookie(session_token))],
            )
            return

        if path == "/api/auth/login":
            payload = self._read_json_body()
            if payload is None:
                return
            try:
                logged_in_username = auth_store.authenticate(
                    str(payload.get("username", "")),
                    str(payload.get("password", "")),
                )
                session_token = auth_store.create_session(logged_in_username)
            except AuthError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            self._send_json(
                {"message": "登录成功。", "username": logged_in_username},
                extra_headers=[("Set-Cookie", self._build_session_cookie(session_token))],
            )
            return

        if path == "/api/auth/logout":
            session_token = self._current_session_token()
            auth_store.destroy_session(session_token)
            self._send_json(
                {"message": "已退出登录。"},
                extra_headers=[("Set-Cookie", self._build_expired_cookie())],
            )
            return

        if not username:
            self._send_json({"error": "请先登录。"}, status=401)
            return

        if path == "/api/ask":
            payload = self._read_json_body()
            if payload is None:
                return
            question = str(payload.get("question", "")).strip()
            if not question:
                self._send_json({"answer": "请输入问题。", "sources": [], "contexts": []}, status=400)
                return
            self._send_json(engine.answer(question))
            return

        if path == "/api/community/posts":
            payload = self._read_json_body()
            if payload is None:
                return
            try:
                post = community_store.create_post(
                    author=username,
                    title=str(payload.get("title", "")),
                    content=str(payload.get("content", "")),
                )
            except CommunityError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json({"message": "发布成功。", "post": post}, status=201)
            return

        comment_match = COMMUNITY_COMMENT_PATH.fullmatch(path)
        if comment_match:
            payload = self._read_json_body()
            if payload is None:
                return
            try:
                comment = community_store.add_comment(
                    post_id=int(comment_match.group("post_id")),
                    author=username,
                    content=str(payload.get("content", "")),
                )
            except CommunityError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json({"message": "评论成功。", "comment": comment}, status=201)
            return

        self.send_error(404, "Not Found")

    def _read_json_body(self) -> dict | None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(content_length).decode("utf-8")
            return json.loads(payload or "{}")
        except (ValueError, json.JSONDecodeError):
            self.send_error(400, "Invalid JSON")
            return None

    def _current_session_token(self) -> str | None:
        raw_cookie = self.headers.get("Cookie", "")
        if not raw_cookie:
            return None
        cookie = SimpleCookie()
        cookie.load(raw_cookie)
        morsel = cookie.get(AUTH_COOKIE_NAME)
        return morsel.value if morsel else None

    def _current_user(self) -> str | None:
        return auth_store.get_session_user(self._current_session_token())

    def _build_session_cookie(self, token: str) -> str:
        return (
            f"{AUTH_COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; "
            f"Max-Age={SESSION_MAX_AGE}"
        )

    def _build_expired_cookie(self) -> str:
        return f"{AUTH_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def _send_json(
        self,
        payload: dict,
        status: int = 200,
        extra_headers: list[tuple[str, str]] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for header_name, header_value in extra_headers or []:
            self.send_header(header_name, header_value)
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = LocalThreadingHTTPServer((HOST, PORT), RAGRequestHandler)
    print(f"果用经济作物知识系统已启动: http://{HOST}:{PORT}")
    print("按 Ctrl+C 停止服务。")
    server.serve_forever()


if __name__ == "__main__":
    main()
