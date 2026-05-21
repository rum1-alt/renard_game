from __future__ import annotations

import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from .game_core import BLACK, EMPTY, WHITE, BoardGame, GameFactory

HOST = "127.0.0.1"
PORT = 8765
STATIC_DIR = Path(__file__).with_name("web")


class GameSession:
    def __init__(self):
        self.game: BoardGame = GameFactory.create("gomoku", 15)
        self.last_message = "已开始五子棋，棋盘大小 15x15。"
        self.lock = threading.Lock()

    def record(self, message: str) -> None:
        self.last_message = message

    def state(self) -> dict:
        return {
            "gameType": self.game.name,
            "displayName": self.game.display_name,
            "size": self.game.size,
            "board": self.game.board,
            "currentPlayer": self.game.current_player,
            "gameOver": self.game.game_over,
            "winner": self.game.winner,
            "status": self.game.status_text(),
            "message": self.last_message,
        }


SESSION = GameSession()


def player_name(player: str | None) -> str:
    if player == BLACK:
        return "黑方"
    if player == WHITE:
        return "白方"
    return "平局"


class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if self.path == "/api/state":
            with SESSION.lock:
                self._send_json(SESSION.state())
            return
        if self.path == "/api/export":
            with SESSION.lock:
                data = SESSION.game.to_data()
            body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=renard_save.json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/static/"):
            file_path = STATIC_DIR / unquote(self.path.removeprefix("/static/"))
            content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            self._send_file(file_path, content_type)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            with SESSION.lock:
                message = self._handle_action(payload)
                if message:
                    SESSION.record(message)
                self._send_json(SESSION.state())
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)

    def _handle_action(self, payload: dict) -> str:
        action = payload.get("action")
        if action == "start":
            game_type = str(payload.get("gameType", "gomoku"))
            size = int(payload.get("size", 15))
            SESSION.game = GameFactory.create(game_type, size)
            return f"已开始{SESSION.game.display_name}，棋盘大小 {size}x{size}。"
        if action == "restart":
            game_type = SESSION.game.name
            size = SESSION.game.size
            SESSION.game = GameFactory.create(game_type, size)
            return f"已重新开始{SESSION.game.display_name}，棋盘大小 {size}x{size}。"
        if action == "move":
            return SESSION.game.place(int(payload["row"]), int(payload["col"]))
        if action == "undo":
            return SESSION.game.undo()
        if action == "resign":
            return SESSION.game.resign()
        if action == "import":
            SESSION.game = BoardGame.from_data(payload["data"])
            return "读取浏览器存档成功。"
        raise ValueError("未知操作。")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body) if body else {}

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.is_file() or STATIC_DIR not in path.resolve().parents and path.resolve() != STATIC_DIR:
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), WebHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"Renard Game GUI running at {url}")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
