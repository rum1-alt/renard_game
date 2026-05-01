from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk

from .game_core import BLACK, EMPTY, WHITE, BoardGame, GameFactory


class BoardCanvas(tk.Canvas):
    def __init__(self, master, on_move):
        super().__init__(master, width=640, height=640, bg="#d7a95f", highlightthickness=0)
        self.on_move = on_move
        self.game: BoardGame | None = None
        self.margin = 36
        self.cell = 1
        self.bind("<Configure>", self._redraw)
        self.bind("<Button-1>", self._handle_click)

    def set_game(self, game: BoardGame | None) -> None:
        self.game = game
        self._redraw()

    def _geometry(self) -> tuple[int, int, int]:
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        board_px = min(width, height) - self.margin * 2
        size = self.game.size if self.game else 8
        cell = max(board_px // (size - 1), 1)
        left = (width - cell * (size - 1)) // 2
        top = (height - cell * (size - 1)) // 2
        self.cell = cell
        return left, top, cell

    def _handle_click(self, event) -> None:
        if self.game is None:
            return
        left, top, cell = self._geometry()
        col = round((event.x - left) / cell)
        row = round((event.y - top) / cell)
        if abs(event.x - (left + col * cell)) > cell * 0.45:
            return
        if abs(event.y - (top + row * cell)) > cell * 0.45:
            return
        self.on_move(row + 1, col + 1)

    def _redraw(self, _event=None) -> None:
        self.delete("all")
        game = self.game
        size = game.size if game else 8
        left, top, cell = self._geometry()
        right = left + cell * (size - 1)
        bottom = top + cell * (size - 1)

        self.create_rectangle(left - 24, top - 24, right + 24, bottom + 24, fill="#d7a95f", outline="#b77f35")
        for i in range(size):
            x = left + i * cell
            y = top + i * cell
            self.create_line(left, y, right, y, fill="#3b2b1f", width=1)
            self.create_line(x, top, x, bottom, fill="#3b2b1f", width=1)
            self.create_text(left - 20, y, text=str(i + 1), fill="#4a3728", font=("Arial", 10))
            self.create_text(x, top - 20, text=str(i + 1), fill="#4a3728", font=("Arial", 10))

        if not game:
            self.create_text((left + right) // 2, (top + bottom) // 2, text="点击“开始游戏”", fill="#4a3728", font=("Arial", 18, "bold"))
            return

        radius = max(cell * 0.38, 7)
        for row in range(size):
            for col in range(size):
                piece = game.board[row][col]
                if piece == EMPTY:
                    continue
                x = left + col * cell
                y = top + row * cell
                if piece == BLACK:
                    fill, outline = "#161616", "#000000"
                else:
                    fill, outline = "#f5f1e8", "#6f6558"
                self.create_oval(x - radius, y - radius, x + radius, y + radius, fill=fill, outline=outline, width=2)


class GameApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Renard Game - 棋类对战平台")
        self.geometry("940x720")
        self.minsize(760, 620)
        self.game: BoardGame | None = None
        self.last_start = ("gomoku", 15)
        self._build_ui()
        self._start_game()

    def _build_ui(self) -> None:
        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=0)
        main.rowconfigure(0, weight=1)

        self.board = BoardCanvas(main, self._place_piece)
        self.board.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        panel = ttk.Frame(main, width=240)
        panel.grid(row=0, column=1, sticky="ns")
        panel.grid_propagate(False)
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="棋类对战平台", font=("Arial", 18, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 16))

        settings = ttk.LabelFrame(panel, text="开局设置", padding=12)
        settings.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="类型").grid(row=0, column=0, sticky="w", pady=4)
        self.game_type = tk.StringVar(value="gomoku")
        ttk.Combobox(
            settings,
            textvariable=self.game_type,
            values=("gomoku", "go"),
            state="readonly",
            width=12,
        ).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(settings, text="大小").grid(row=1, column=0, sticky="w", pady=4)
        self.board_size = tk.IntVar(value=15)
        ttk.Spinbox(settings, from_=8, to=19, textvariable=self.board_size, width=6).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Button(settings, text="开始游戏", command=self._start_game).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        actions = ttk.LabelFrame(panel, text="对局操作", padding=12)
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        actions.columnconfigure(0, weight=1)
        ttk.Button(actions, text="重新开始", command=self._restart_game).grid(row=0, column=0, sticky="ew", pady=3)
        ttk.Button(actions, text="悔棋一步", command=self._undo).grid(row=1, column=0, sticky="ew", pady=3)
        ttk.Button(actions, text="围棋虚着", command=self._pass_turn).grid(row=2, column=0, sticky="ew", pady=3)
        ttk.Button(actions, text="投子认负", command=self._resign).grid(row=3, column=0, sticky="ew", pady=3)

        archive = ttk.LabelFrame(panel, text="存档", padding=12)
        archive.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        archive.columnconfigure(0, weight=1)
        ttk.Button(archive, text="保存局面", command=self._save_game).grid(row=0, column=0, sticky="ew", pady=3)
        ttk.Button(archive, text="读取存档", command=self._load_game).grid(row=1, column=0, sticky="ew", pady=3)

        status_box = ttk.LabelFrame(panel, text="状态", padding=12)
        status_box.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        self.status = tk.StringVar(value="尚未开始")
        ttk.Label(status_box, textvariable=self.status, wraplength=210, justify="left").grid(row=0, column=0, sticky="w")

        log_box = ttk.LabelFrame(panel, text="操作反馈", padding=8)
        log_box.grid(row=5, column=0, sticky="nsew")
        panel.rowconfigure(5, weight=1)
        log_box.rowconfigure(0, weight=1)
        log_box.columnconfigure(0, weight=1)
        self.log = tk.Text(log_box, width=28, height=12, wrap="word", state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")

    def _start_game(self) -> None:
        try:
            game_type = self.game_type.get()
            size = int(self.board_size.get())
            self.game = GameFactory.create(game_type, size)
            self.last_start = (game_type, size)
            self._append_log(f"已开始 {self.game.display_name}，棋盘大小 {size}x{size}。")
            self._refresh()
        except Exception as exc:
            self._append_log(f"错误：{exc}")

    def _restart_game(self) -> None:
        game_type, size = self.last_start
        self.game_type.set(game_type)
        self.board_size.set(size)
        self._start_game()

    def _place_piece(self, row: int, col: int) -> None:
        if self.game is None:
            self._append_log("请先开始游戏。")
            return
        message = self.game.place(row, col)
        self._append_log(message)
        self._refresh()

    def _undo(self) -> None:
        if self.game is None:
            self._append_log("请先开始游戏。")
            return
        self._append_log(self.game.undo())
        self._refresh()

    def _pass_turn(self) -> None:
        if self.game is None:
            self._append_log("请先开始游戏。")
            return
        self._append_log(self.game.pass_turn())
        self._refresh()

    def _resign(self) -> None:
        if self.game is None:
            self._append_log("请先开始游戏。")
            return
        self._append_log(self.game.resign())
        self._refresh()

    def _save_game(self) -> None:
        if self.game is None:
            self._append_log("请先开始游戏。")
            return
        filename = filedialog.asksaveasfilename(
            title="保存局面",
            defaultextension=".json",
            filetypes=(("JSON 存档", "*.json"), ("所有文件", "*.*")),
        )
        if not filename:
            self._append_log("已取消保存。")
            return
        try:
            self._append_log(self.game.save(filename))
        except Exception as exc:
            self._append_log(f"保存失败：{exc}")

    def _load_game(self) -> None:
        filename = filedialog.askopenfilename(
            title="读取存档",
            filetypes=(("JSON 存档", "*.json"), ("所有文件", "*.*")),
        )
        if not filename:
            self._append_log("已取消读取。")
            return
        try:
            self.game = BoardGame.load(filename)
            self.last_start = (self.game.name, self.game.size)
            self.game_type.set(self.game.name)
            self.board_size.set(self.game.size)
            self._append_log(f"读取存档成功：{filename}")
            self._refresh()
        except Exception as exc:
            self._append_log(f"读取失败：{exc}")

    def _refresh(self) -> None:
        self.board.set_game(self.game)
        self.status.set(self.game.status_text() if self.game else "尚未开始")

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def main() -> None:
    app = GameApp()
    app.mainloop()
