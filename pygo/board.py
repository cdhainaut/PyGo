"""Board replay and capture statistics.

Replays recorded moves: stones are placed and captured opponent groups removed,
without legality checks (ko, suicide) — the game record is taken as given.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from .models import Color, Game, Stone

Point = tuple[int, int]


class Board:
    """Mutable goban state: stones placed, opponent groups captured."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._grid: list[list[Color | None]] = [[None] * width for _ in range(height)]

    def setup(self, stones: Iterable[Stone]) -> None:
        """Place setup stones (handicap) without capture logic."""
        for stone in stones:
            self._grid[stone.y][stone.x] = stone.color

    def play(self, color: Color, x: int, y: int) -> int:
        """Place a stone and remove captured opponent groups; return captured count."""
        if self._grid[y][x] is not None:
            raise ValueError(f"point ({x}, {y}) is already occupied")
        self._grid[y][x] = color
        captured = 0
        for nx, ny in self._neighbors(x, y):
            if self._grid[ny][nx] not in (None, color):
                group, liberties = self._group(nx, ny)
                if not liberties:
                    captured += len(group)
                    for gx, gy in group:
                        self._grid[gy][gx] = None
        return captured

    def stones(self, color: Color) -> int:
        """Number of stones of one color on the board."""
        return sum(1 for row in self._grid for cell in row if cell == color)

    def _neighbors(self, x: int, y: int) -> Iterator[Point]:
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield nx, ny

    def _group(self, x: int, y: int) -> tuple[set[Point], set[Point]]:
        """Connected stones of the point and their liberties."""
        color = self._grid[y][x]
        group: set[Point] = set()
        liberties: set[Point] = set()
        frontier: list[Point] = [(x, y)]
        while frontier:
            px, py = frontier.pop()
            if (px, py) in group:
                continue
            group.add((px, py))
            for nx, ny in self._neighbors(px, py):
                cell = self._grid[ny][nx]
                if cell is None:
                    liberties.add((nx, ny))
                elif cell == color:
                    frontier.append((nx, ny))
        return group, liberties


@dataclass(frozen=True)
class CaptureStats:
    """Stones captured by one color during the game."""

    color: Color
    stones: int
    capturing_moves: int
    first_capture_move: int | None  # 1-based
    largest_capture: int
    largest_capture_move: int | None  # 1-based


def capture_counts(game: Game) -> tuple[int, ...]:
    """Stones captured at each move index (0 for passes and quiet moves)."""
    board = Board(game.board_width, game.board_height)
    board.setup(game.initial_stones)
    counts = []
    for index, move in enumerate(game.moves):
        if move.is_pass:
            counts.append(0)
        else:
            counts.append(board.play(game.move_color(index), move.x, move.y))
    return tuple(counts)


def capture_stats(game: Game, color: Color) -> CaptureStats:
    """Capture statistics of one color over the moves they played."""
    own = [
        (index + 1, count)
        for index, count in enumerate(capture_counts(game))
        if count and game.move_color(index) == color
    ]
    if not own:
        return CaptureStats(color, 0, 0, None, 0, None)
    largest_move, largest = max(own, key=lambda item: item[1])
    return CaptureStats(
        color=color,
        stones=sum(count for _, count in own),
        capturing_moves=len(own),
        first_capture_move=own[0][0],
        largest_capture=largest,
        largest_capture_move=largest_move,
    )
