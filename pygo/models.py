"""Typed models for OGS game records: players, setup stones and moves.

Input parsing lives here (OGS JSON), output formatting lives in :mod:`pygo.sgf`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from .config import game_web_url

Color = Literal["black", "white"]

_DAN_THRESHOLD = 30  # OGS internal rank scale: 30 == 1 dan
_PRO_OFFSET = 36  # OGS internal rank scale for professionals
_COLOR_BY_NUMBER = {1: "black", 2: "white"}  # JGOFNumericPlayerColor

POINT_ALPHABET = "abcdefghijklmnopqrstuvwxyz"  # SGF/OBS point encoding: "qd" = (16, 3)


class GameDataError(ValueError):
    """Raised when a payload does not match the OGS game schema."""


def ogs_rank_label(rank: float, professional: bool = False) -> str:
    """OGS internal rank to its display label, e.g. 21.06 -> "9k", 31.2 -> "2d"."""
    if professional:
        return f"{round(rank) - _PRO_OFFSET}p"
    if rank < _DAN_THRESHOLD:
        return f"{math.ceil(_DAN_THRESHOLD - rank)}k"
    return f"{math.floor(rank - _DAN_THRESHOLD) + 1}d"


@dataclass(frozen=True)
class Player:
    name: str
    rank: float | None = None
    professional: bool = False

    @property
    def rank_label(self) -> str | None:
        """Display rank such as "9k" or "4d", None when unknown."""
        if self.rank is None:
            return None
        return ogs_rank_label(self.rank, self.professional)


@dataclass(frozen=True)
class Stone:
    color: Color
    x: int
    y: int


@dataclass(frozen=True)
class Move:
    """One played move.

    Packed by OGS as ``[x, y, think_time?, color?, extras?]``. ``think_time_ms``
    is the time spent before the move; ``color`` overrides the strict alternation
    for edited games; ``blur_ms`` and ``sgf_downloaded_by`` are the OGS fair-play
    extras ("typically restricted information", often absent from public data).
    """

    x: int
    y: int
    think_time_ms: float | None = None
    color: Color | None = None
    blur_ms: float | None = None
    sgf_downloaded_by: tuple[int, ...] = ()
    edited: bool = False

    @property
    def is_pass(self) -> bool:
        """OGS encodes a pass as negative coordinates."""
        return self.x < 0 or self.y < 0


@dataclass(frozen=True)
class Game:
    """One OGS game: metadata, setup stones and the played moves.

    Coordinates are 0-based board indices, x = column, y = row, both from the
    top-left corner (the OGS convention, identical to SGF points).
    """

    game_id: int
    name: str
    black: Player
    white: Player
    board_width: int
    board_height: int
    komi: float
    rules: str
    handicap: int
    initial_player: Color
    outcome: str | None
    winner: Color | None
    start_time: datetime | None
    initial_stones: tuple[Stone, ...]
    moves: tuple[Move, ...]

    @property
    def source_url(self) -> str:
        return game_web_url(self.game_id)

    def player(self, color: Color) -> Player:
        return self.black if color == "black" else self.white

    def move_color(self, index: int) -> Color:
        """Color playing move `index`: explicit override, else strict alternation."""
        explicit = self.moves[index].color
        if explicit is not None:
            return explicit
        black_plays = (index % 2 == 0) == (self.initial_player == "black")
        return "black" if black_plays else "white"

    @classmethod
    def from_ogs_json(cls, data: dict) -> Game:
        """Build a game from an OGS `/api/v1/games/<id>` payload."""
        try:
            gamedata = data["gamedata"]
            players = gamedata["players"]
            black_raw, white_raw = players["black"], players["white"]
            return cls(
                game_id=gamedata["game_id"],
                name=gamedata.get("game_name", ""),
                black=_parse_player(black_raw),
                white=_parse_player(white_raw),
                board_width=gamedata["width"],
                board_height=gamedata["height"],
                komi=gamedata["komi"],
                rules=gamedata["rules"],
                handicap=gamedata.get("handicap", 0),
                initial_player=gamedata["initial_player"],
                outcome=gamedata.get("outcome"),
                winner=_parse_winner(gamedata.get("winner"), black_raw, white_raw),
                start_time=_parse_start_time(gamedata.get("start_time")),
                initial_stones=_parse_stones(gamedata.get("initial_state") or {}),
                moves=tuple(_parse_move(raw) for raw in gamedata["moves"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GameDataError(f"not an OGS game payload: {exc}") from exc


def _parse_player(raw: dict) -> Player:
    return Player(
        name=raw["username"],
        rank=raw.get("rank"),
        professional=bool(raw.get("professional", False)),
    )


def _parse_winner(winner_id, black_raw: dict, white_raw: dict) -> Color | None:
    if winner_id is None:
        return None
    if winner_id == black_raw["id"]:
        return "black"
    if winner_id == white_raw["id"]:
        return "white"
    raise GameDataError(f"winner id {winner_id} is not a player of the game")


def _parse_start_time(timestamp) -> datetime | None:
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _parse_stones(initial_state: dict) -> tuple[Stone, ...]:
    stones = []
    for color in ("black", "white"):
        encoded = initial_state.get(color) or ""
        for i in range(0, len(encoded) - 1, 2):
            x, y = POINT_ALPHABET.index(encoded[i]), POINT_ALPHABET.index(encoded[i + 1])
            stones.append(Stone(color=color, x=x, y=y))
    return tuple(stones)


def _parse_move(raw: list | tuple) -> Move:
    """AdHocPackedMove: [x, y, time_delta?, JGOFNumericPlayerColor?, extras?]."""
    tail = list(raw[3:])
    extras = [item for item in tail if isinstance(item, dict)]
    extra = extras[-1] if extras else {}
    color = _COLOR_BY_NUMBER.get(tail[0]) if tail and isinstance(tail[0], int) else None
    think_time_ms = raw[2] if len(raw) > 2 and isinstance(raw[2], (int, float)) else None
    return Move(
        x=int(raw[0]),
        y=int(raw[1]),
        think_time_ms=float(think_time_ms) if think_time_ms is not None else None,
        color=color,
        blur_ms=extra.get("blur"),
        sgf_downloaded_by=tuple(int(user) for user in extra.get("sgf_downloaded_by", [])),
        edited=bool(extra.get("edited", False)),
    )
