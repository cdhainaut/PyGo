"""Board replay: capture detection and capture statistics."""

import pytest

from pygo.board import Board, capture_counts, capture_stats
from pygo.models import Stone


def test_single_stone_capture():
    board = Board(9, 9)
    board.play("white", 4, 3)
    board.play("black", 3, 3)
    board.play("black", 5, 3)
    board.play("black", 4, 2)
    assert board.play("black", 4, 4) == 1
    assert board.stones("white") == 0
    assert board.stones("black") == 4


def test_two_groups_captured_at_once():
    board = Board(9, 9)
    board.play("white", 0, 1)
    board.play("white", 1, 0)
    board.play("black", 0, 2)
    board.play("black", 1, 1)
    board.play("black", 2, 0)
    assert board.play("black", 0, 0) == 2
    assert board.stones("white") == 0


def test_setup_stones_can_be_captured():
    board = Board(9, 9)
    board.setup([Stone(color="white", x=4, y=4)])
    board.play("black", 4, 3)
    board.play("black", 4, 5)
    board.play("black", 3, 4)
    assert board.play("black", 5, 4) == 1
    assert board.stones("white") == 0


def test_occupied_point_raises():
    board = Board(9, 9)
    board.play("black", 3, 3)
    with pytest.raises(ValueError):
        board.play("white", 3, 3)


def test_capture_counts(game_34508515):
    counts = capture_counts(game_34508515)
    assert len(counts) == 51
    assert sum(counts) == 7
    assert counts[47] == 5  # largest capture of the game, move 48
    assert all(count == 0 for count in counts[-2:])  # last two moves are passes


def test_capture_stats(game_34508515):
    black = capture_stats(game_34508515, "black")
    assert (black.stones, black.capturing_moves, black.first_capture_move) == (1, 1, 49)
    assert (black.largest_capture, black.largest_capture_move) == (1, 49)
    white = capture_stats(game_34508515, "white")
    assert (white.stones, white.capturing_moves, white.first_capture_move) == (6, 2, 46)
    assert (white.largest_capture, white.largest_capture_move) == (5, 48)


def test_handicap_game_captures(game_40476992):
    assert sum(capture_counts(game_40476992)) == 1
    black = capture_stats(game_40476992, "black")
    assert (black.stones, black.first_capture_move) == (1, 90)
    white = capture_stats(game_40476992, "white")
    assert (white.stones, white.capturing_moves, white.first_capture_move) == (0, 0, None)
