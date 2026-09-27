"""Minimal SGF writer for OGS games.

Renders one game as a flat SGF tree: root properties, optional setup stones,
then one node per move. OGS passes (negative coordinates) become empty moves
(`;B[]`), as the SGF standard requires.
"""

from __future__ import annotations

import re

from .events import move_events
from .models import POINT_ALPHABET, Color, Game

_RULES_LABELS = {"japanese": "Japanese", "chinese": "Chinese", "aga": "AGA", "nz": "New Zealand"}
_RESULT_SUFFIXES = {"Resignation": "R", "Timeout": "T", "Forfeit": "F"}
_POINTS_RESULT = re.compile(r"([\d.]+) points?")


def sgf_point(x: int, y: int) -> str:
    """Board indices to an SGF point, e.g. (16, 3) -> "qd"."""
    return f"{POINT_ALPHABET[x]}{POINT_ALPHABET[y]}"


def sgf_result(outcome: str | None, winner: Color | None) -> str | None:
    """OGS outcome text to the SGF RE value, e.g. "17.5 points" -> "W+17.5"."""
    if outcome is None:
        return None
    if winner is None:
        return "0" if outcome.lower() == "draw" else outcome
    tag = "B" if winner == "black" else "W"
    scored = _POINTS_RESULT.fullmatch(outcome)
    if scored:
        return f"{tag}+{scored.group(1)}"
    return f"{tag}+{_RESULT_SUFFIXES.get(outcome, outcome)}"


def to_sgf(game: Game, annotate: bool = False) -> str:
    """Render a game as an SGF tree string (without trailing newline).

    With `annotate`, flagged moves (blur, mid-game SGF downloads, edits) carry a
    C[] comment with the event detail.
    """
    moves = _move_nodes(game, annotate)
    lines = ["(;", *_root_properties(game), *_setup_properties(game), *moves, ")"]
    return "\n".join(lines)


def _root_properties(game: Game) -> list[str]:
    width, height = game.board_width, game.board_height
    fields = {
        "FF": "4",
        "CA": "UTF-8",
        "GM": "1",
        "DT": game.start_time.date().isoformat() if game.start_time else None,
        "PC": f"OGS: {game.source_url}",
        "GN": game.name,
        "PB": game.black.name,
        "PW": game.white.name,
        "BR": game.black.rank_label,
        "WR": game.white.rank_label,
        "RE": sgf_result(game.outcome, game.winner),
        "SZ": str(width) if width == height else f"{width}:{height}",
        "KM": f"{game.komi:g}",
        "RU": _RULES_LABELS.get(game.rules, game.rules.capitalize()),
        "HA": str(game.handicap) if game.handicap >= 2 else None,
    }
    return [f"{tag}[{_escape(value)}]" for tag, value in fields.items() if value is not None]


def _setup_properties(game: Game) -> list[str]:
    props = []
    for tag, color in (("AB", "black"), ("AW", "white")):
        points = [sgf_point(s.x, s.y) for s in game.initial_stones if s.color == color]
        if points:
            props.append(f"{tag}[{']['.join(points)}]")
    return props


def _move_nodes(game: Game, annotate: bool = False) -> list[str]:
    comments: dict[int, list[str]] = {}
    if annotate:
        for event in move_events(game):
            comments.setdefault(event.move_number, []).append(event.detail)
    nodes = []
    for index, move in enumerate(game.moves):
        tag = "B" if game.move_color(index) == "black" else "W"
        point = "" if move.is_pass else sgf_point(move.x, move.y)
        node = f";{tag}[{point}]"
        if index + 1 in comments:
            node += f"C[{_escape('; '.join(comments[index + 1]))}]"
        nodes.append(node)
    return nodes


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("]", "\\]")
