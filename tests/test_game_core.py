import copy
import json
import tempfile
import unittest
from pathlib import Path

from dataclasses import asdict

from renard_game.game_core import BLACK, EMPTY, WHITE, BoardGame, GameFactory, GoGame


class GomokuRuleTest(unittest.TestCase):
    def test_black_wins_after_five_in_row(self):
        game = GameFactory.create("gomoku", 8)
        for row, col in [(1, 1), (2, 1), (1, 2), (2, 2), (1, 3), (2, 3), (1, 4), (2, 4)]:
            game.place(row, col)

        message = game.place(1, 5)

        self.assertIn("连成五子", message)
        self.assertTrue(game.game_over)
        self.assertEqual(game.winner, BLACK)


class GoRuleTest(unittest.TestCase):
    def test_capture_removes_stones_without_liberties(self):
        game = GoGame(8)
        game.board[1][1] = WHITE
        game.board[0][1] = BLACK
        game.board[2][1] = BLACK
        game.board[1][0] = BLACK
        game.current_player = BLACK

        message = game.place(2, 3)

        self.assertIn("提子 1", message)
        self.assertEqual(game.board[1][1], EMPTY)

    def test_suicide_move_is_rejected(self):
        game = GoGame(8)
        game.board[0][1] = BLACK
        game.board[1][0] = BLACK
        game.current_player = WHITE

        message = game.place(1, 1)

        self.assertIn("自杀手", message)
        self.assertEqual(game.board[0][0], EMPTY)
        self.assertEqual(game.current_player, WHITE)

    def test_immediate_ko_retake_is_rejected(self):
        game = GoGame(8)
        game.board[1][1] = WHITE
        game.board[2][0] = WHITE
        game.board[2][2] = WHITE
        game.board[3][1] = WHITE
        game.board[1][2] = BLACK
        game.board[2][3] = BLACK
        game.board[3][2] = BLACK
        game.current_player = BLACK
        before_capture = copy.deepcopy(game.board)

        capture_message = game.place(3, 2)
        retake_message = game.place(3, 3)

        self.assertIn("提子 1", capture_message)
        self.assertIn("重复局面", retake_message)
        self.assertNotEqual(game.board, before_capture)
        self.assertEqual(game.board[2][1], BLACK)
        self.assertEqual(game.board[2][2], EMPTY)
        self.assertEqual(game.current_player, WHITE)

    def test_no_legal_move_detection_on_full_board(self):
        game = GoGame(8)
        game.board = [[BLACK for _ in range(game.size)] for _ in range(game.size)]

        self.assertFalse(game.has_any_legal_move(WHITE))


class SaveLoadTest(unittest.TestCase):
    def test_save_and_load_keeps_board_state(self):
        game = GameFactory.create("gomoku", 8)
        game.place(1, 1)
        game.place(2, 2)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.json"
            game.save(str(path))
            loaded = BoardGame.load(str(path))

        self.assertEqual(loaded.name, "gomoku")
        self.assertEqual(loaded.board[0][0], BLACK)
        self.assertEqual(loaded.board[1][1], WHITE)

    def test_load_rejects_board_with_wrong_shape(self):
        game = GameFactory.create("gomoku", 8)
        snapshot = game.snapshot()
        snapshot.board = [[EMPTY]]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            data = {"type": "gomoku", "size": 8, "snapshot": asdict(snapshot)}
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                BoardGame.load(str(path))


if __name__ == "__main__":
    unittest.main()
