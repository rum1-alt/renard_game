from __future__ import annotations

import copy
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path

EMPTY = "."
BLACK = "B"
WHITE = "W"


def opponent(player: str) -> str:
    return WHITE if player == BLACK else BLACK


def player_label(player: str | None) -> str:
    if player == BLACK:
        return "黑方"
    if player == WHITE:
        return "白方"
    return "平局"


@dataclass
class GameSnapshot:
    board: list[list[str]]
    current_player: str
    game_over: bool
    winner: str | None
    pass_count: int = 0


class BoardGame(ABC):
    name = "board"
    display_name = "棋类"

    def __init__(self, size: int):
        if size < 8 or size > 19:
            raise ValueError("棋盘大小必须在 8 到 19 之间。")
        self.size = size
        self.board = [[EMPTY for _ in range(size)] for _ in range(size)]
        self.current_player = BLACK
        self.game_over = False
        self.winner: str | None = None
        self.history: list[GameSnapshot] = []
        self.pass_count = 0

    def snapshot(self) -> GameSnapshot:
        return GameSnapshot(
            copy.deepcopy(self.board),
            self.current_player,
            self.game_over,
            self.winner,
            self.pass_count,
        )

    def restore(self, snap: GameSnapshot) -> None:
        self.board = copy.deepcopy(snap.board)
        self.current_player = snap.current_player
        self.game_over = snap.game_over
        self.winner = snap.winner
        self.pass_count = snap.pass_count

    def switch_player(self) -> None:
        self.current_player = opponent(self.current_player)

    def is_inside(self, row: int, col: int) -> bool:
        return 0 <= row < self.size and 0 <= col < self.size

    def place(self, row: int, col: int) -> str:
        if self.game_over:
            return "棋局已结束，请重新开始或读取存档。"
        row -= 1
        col -= 1
        if not self.is_inside(row, col):
            return "落子位置超出棋盘。"
        if self.board[row][col] != EMPTY:
            return "该位置已有棋子。"
        self.history.append(self.snapshot())
        return self._place(row, col)

    @abstractmethod
    def _place(self, row: int, col: int) -> str:
        pass

    def pass_turn(self) -> str:
        return "当前游戏不支持虚着。"

    def resign(self) -> str:
        if self.game_over:
            return "棋局已经结束。"
        self.history.append(self.snapshot())
        self.winner = opponent(self.current_player)
        self.game_over = True
        return f"{player_label(self.current_player)}投子认负，{player_label(self.winner)}获胜。"

    def undo(self) -> str:
        if not self.history:
            return "无棋子可悔。"
        self.restore(self.history.pop())
        return "已悔棋一步。"

    def save(self, filename: str) -> str:
        Path(filename).write_text(json.dumps(self.to_data(), ensure_ascii=False, indent=2), encoding="utf-8")
        return f"局面已保存到 {filename}"

    def to_data(self) -> dict:
        return {
            "type": self.name,
            "size": self.size,
            "snapshot": asdict(self.snapshot()),
        }

    @classmethod
    def load(cls, filename: str) -> "BoardGame":
        data = json.loads(Path(filename).read_text(encoding="utf-8"))
        return cls.from_data(data)

    @classmethod
    def from_data(cls, data: dict) -> "BoardGame":
        if not isinstance(data, dict):
            raise ValueError("存档格式不合法。")
        game_type = data.get("type")
        size = data.get("size")
        snap_data = data.get("snapshot")
        if not isinstance(game_type, str) or not isinstance(size, int) or not isinstance(snap_data, dict):
            raise ValueError("存档缺少必要字段。")
        game = GameFactory.create(game_type, size)
        snapshot = GameSnapshot(**snap_data)
        if snapshot.current_player not in {BLACK, WHITE}:
            raise ValueError("存档当前行棋方不合法。")
        if snapshot.winner not in {BLACK, WHITE, None}:
            raise ValueError("存档胜者不合法。")
        if not isinstance(snapshot.game_over, bool) or not isinstance(snapshot.pass_count, int) or snapshot.pass_count < 0:
            raise ValueError("存档状态字段不合法。")
        if len(snapshot.board) != size or any(len(row) != size for row in snapshot.board):
            raise ValueError("存档棋盘大小不匹配。")
        legal_cells = {EMPTY, BLACK, WHITE}
        if any(cell not in legal_cells for row in snapshot.board for cell in row):
            raise ValueError("存档棋盘包含非法棋子。")
        game.restore(snapshot)
        return game

    def status_text(self) -> str:
        if self.game_over:
            return f"棋局结束：{player_label(self.winner)}"
        return f"当前行棋方：{player_label(self.current_player)}"


class GomokuGame(BoardGame):
    name = "gomoku"
    display_name = "五子棋"

    def _place(self, row: int, col: int) -> str:
        self.board[row][col] = self.current_player
        player = self.current_player
        self.pass_count = 0
        if self.has_five(row, col):
            self.game_over = True
            self.winner = player
            return f"{player_label(player)}在 ({row + 1},{col + 1}) 落子并连成五子，获胜。"
        if all(cell != EMPTY for line in self.board for cell in line):
            self.game_over = True
            return f"{player_label(player)}落子后棋盘已满，平局。"
        self.switch_player()
        return f"{player_label(player)}在 ({row + 1},{col + 1}) 落子成功。"

    def has_five(self, row: int, col: int) -> bool:
        player = self.board[row][col]
        for dr, dc in [(1, 0), (0, 1), (1, 1), (1, -1)]:
            count = 1
            for sign in [1, -1]:
                nr, nc = row + dr * sign, col + dc * sign
                while self.is_inside(nr, nc) and self.board[nr][nc] == player:
                    count += 1
                    nr += dr * sign
                    nc += dc * sign
            if count >= 5:
                return True
        return False


class GoGame(BoardGame):
    name = "go"
    display_name = "围棋"

    def neighbors(self, row: int, col: int):
        for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nr, nc = row + dr, col + dc
            if self.is_inside(nr, nc):
                yield nr, nc

    def group_and_liberties(self, row: int, col: int) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        return self.group_and_liberties_on(self.board, row, col)

    def group_and_liberties_on(
        self,
        board: list[list[str]],
        row: int,
        col: int,
    ) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        color = board[row][col]
        stack = [(row, col)]
        group = set()
        liberties = set()
        while stack:
            r, c = stack.pop()
            if (r, c) in group:
                continue
            group.add((r, c))
            for nr, nc in self.neighbors(r, c):
                if board[nr][nc] == EMPTY:
                    liberties.add((nr, nc))
                elif board[nr][nc] == color:
                    stack.append((nr, nc))
        return group, liberties

    def _place(self, row: int, col: int) -> str:
        player = self.current_player
        next_board, captured, error = self.simulate_move(row, col, player)
        if error:
            self.restore(self.history.pop())
            return error
        self.board = next_board
        self.pass_count = 0
        self.switch_player()
        message = f"{player_label(player)}在 ({row + 1},{col + 1}) 落子成功，提子 {captured} 枚。"
        if not self.has_any_legal_move(self.current_player):
            self.finish_by_score()
            return message + f"{player_label(self.current_player)}无合法落点，{self.score_text()}"
        return message

    def simulate_move(self, row: int, col: int, player: str) -> tuple[list[list[str]], int, str | None]:
        next_board = copy.deepcopy(self.board)
        next_board[row][col] = player
        captured = 0
        for nr, nc in list(self.neighbors(row, col)):
            if next_board[nr][nc] == opponent(player):
                group, liberties = self.group_and_liberties_on(next_board, nr, nc)
                if not liberties:
                    captured += len(group)
                    for gr, gc in group:
                        next_board[gr][gc] = EMPTY
        own_group, own_liberties = self.group_and_liberties_on(next_board, row, col)
        if not own_liberties:
            return next_board, captured, "该落子属于自杀手，位置不合法。"
        if self.is_repeated_position(next_board):
            return next_board, captured, "该落子会造成重复局面，违反打劫规则。"
        return next_board, captured, None

    def is_repeated_position(self, board: list[list[str]]) -> bool:
        board_key = tuple(tuple(row) for row in board)
        return any(tuple(tuple(row) for row in snap.board) == board_key for snap in self.history)

    def has_any_legal_move(self, player: str) -> bool:
        for row in range(self.size):
            for col in range(self.size):
                if self.board[row][col] != EMPTY:
                    continue
                _, _, error = self.simulate_move(row, col, player)
                if error is None:
                    return True
        return False

    def pass_turn(self) -> str:
        if self.game_over:
            return "棋局已经结束。"
        self.history.append(self.snapshot())
        player = self.current_player
        self.pass_count += 1
        if self.pass_count >= 2:
            self.finish_by_score()
            return f"{player_label(player)}虚着，双方连续虚着。{self.score_text()}"
        self.switch_player()
        return f"{player_label(player)}选择虚着。"

    def finish_by_score(self) -> None:
        black_score, white_score = self.area_scores()
        self.game_over = True
        self.winner = BLACK if black_score > white_score else WHITE if white_score > black_score else None

    def area_scores(self) -> tuple[int, int]:
        visited = set()
        scores = {BLACK: 0, WHITE: 0}
        for r in range(self.size):
            for c in range(self.size):
                color = self.board[r][c]
                if color in (BLACK, WHITE):
                    scores[color] += 1
                elif (r, c) not in visited:
                    region, borders = self.empty_region(r, c)
                    visited |= region
                    if len(borders) == 1:
                        scores[next(iter(borders))] += len(region)
        return scores[BLACK], scores[WHITE]

    def empty_region(self, row: int, col: int) -> tuple[set[tuple[int, int]], set[str]]:
        stack = [(row, col)]
        region = set()
        borders = set()
        while stack:
            r, c = stack.pop()
            if (r, c) in region:
                continue
            region.add((r, c))
            for nr, nc in self.neighbors(r, c):
                color = self.board[nr][nc]
                if color == EMPTY and (nr, nc) not in region:
                    stack.append((nr, nc))
                elif color in (BLACK, WHITE):
                    borders.add(color)
        return region, borders

    def score_text(self) -> str:
        black_score, white_score = self.area_scores()
        winner = player_label(self.winner)
        return f"终局计分：黑={black_score}，白={white_score}，结果={winner}。"


class GameFactory:
    @staticmethod
    def create(game_type: str, size: int) -> BoardGame:
        if game_type in ("gomoku", "五子棋"):
            return GomokuGame(size)
        if game_type in ("go", "围棋"):
            return GoGame(size)
        raise ValueError("未知游戏类型。")
