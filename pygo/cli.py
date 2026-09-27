"""Command line interface: convert OGS games to SGF and summarise them."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

import requests

from .board import capture_stats
from .events import move_events, time_summary, timing_indicators
from .models import Game, GameDataError
from .ogs import fetch_game, fetch_game_json, fetch_player_game_ids
from .sgf import sgf_result, to_sgf


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="py-go", description="Convert and inspect Online-Go (OGS) games."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    convert = subparsers.add_parser("convert", help="export a game as SGF")
    convert.add_argument("source", help="OGS game URL, game id, or path to a saved game JSON")
    convert.add_argument("-o", "--output", type=Path, help="output SGF file (default: stdout)")
    convert.add_argument(
        "--annotate", action="store_true", help="add C[] comments on flagged moves"
    )
    info = subparsers.add_parser("info", help="print a one-screen summary of a game")
    info.add_argument("source", help="OGS game URL, game id, or path to a saved game JSON")
    report = subparsers.add_parser("report", help="fair-play events and think-time report")
    report.add_argument("source", help="OGS game URL, game id, or path to a saved game JSON")
    report.add_argument("--json", action="store_true", help="machine-readable output")
    fetch = subparsers.add_parser("fetch", help="download the games of a player as JSON")
    fetch.add_argument("source", help="player id, username, or OGS user URL")
    fetch.add_argument("-o", "--output-dir", type=Path, default=Path("."), help="target directory")
    fetch.add_argument("--limit", type=int, help="number of most recent games to consider")
    return parser.parse_args(argv)


def load_game(source: str) -> Game:
    """Read a game from a local JSON file or from the OGS API."""
    path = Path(source)
    if path.is_file():
        return Game.from_ogs_json(json.loads(path.read_text(encoding="utf-8")))
    return fetch_game(source)


def info_lines(game: Game) -> list[str]:
    passes = sum(move.is_pass for move in game.moves)
    setup = len(game.initial_stones)
    size = f"{game.board_width}x{game.board_height}"
    result = sgf_result(game.outcome, game.winner) or "unfinished"
    second = f"{size} | {game.rules} rules | komi {game.komi:g}"
    if game.handicap >= 2 or setup:
        second += f" | handicap {game.handicap}"
    third = f"result {result} | {len(game.moves)} moves ({passes} passes)"
    if setup:
        third += f" | {setup} setup stones"
    return [
        f"Game {game.game_id}: {game.black.name} ({game.black.rank_label}) vs. "
        f"{game.white.name} ({game.white.rank_label})",
        f"{game.start_time.date() if game.start_time else 'unknown date'} | {second}",
        third,
        game.source_url,
    ]


def _count(n: int, word: str) -> str:
    """Human count with plural, e.g. 1 -> '1 move', 2 -> '2 moves'."""
    return f"{n} {word}" + ("s" if n != 1 else "")


def report_lines(game: Game) -> list[str]:
    lines = info_lines(game) + ["", "Think time"]
    for color in ("black", "white"):
        summary = time_summary(game, color)
        if summary.timed_moves:
            lines.append(
                f"  {color}: {_count(summary.timed_moves, 'move')} | total {summary.total_s:.0f} s"
                f" | mean {summary.mean_s:.1f} s | median {summary.median_s:.1f} s"
                f" | max {summary.max_s:.1f} s (move {summary.slowest_move})"
                f" | cv {summary.cv:.2f} | blitz {summary.blitz_share:.0%}"
            )
        else:
            lines.append(f"  {color}: no move timing")
    lines += ["", "Captures"]
    for color in ("black", "white"):
        captures = capture_stats(game, color)
        if captures.stones:
            lines.append(
                f"  {color}: {_count(captures.stones, 'stone')}"
                f" in {_count(captures.capturing_moves, 'move')}"
                f" | first move {captures.first_capture_move}"
                f" | largest {captures.largest_capture} (move {captures.largest_capture_move})"
            )
        else:
            lines.append(f"  {color}: none")
    events = move_events(game)
    lines += ["", f"Events ({len(events)})"]
    lines += [f"  move {e.move_number} ({e.color}): {e.detail}" for e in events] or ["  none"]
    indicators = timing_indicators(game)
    lines += ["", f"Indicators ({len(indicators)})"]
    lines += [f"  {i.color}: {i.detail}" for i in indicators] or ["  none"]
    return lines


def report_payload(game: Game) -> dict:
    return {
        "game": {
            "id": game.game_id,
            "name": game.name,
            "url": game.source_url,
            "date": game.start_time.date().isoformat() if game.start_time else None,
            "board": [game.board_width, game.board_height],
            "rules": game.rules,
            "komi": game.komi,
            "handicap": game.handicap,
            "black": {"name": game.black.name, "rank": game.black.rank_label},
            "white": {"name": game.white.name, "rank": game.white.rank_label},
            "result": sgf_result(game.outcome, game.winner),
            "moves": len(game.moves),
        },
        "think_time": [asdict(time_summary(game, color)) for color in ("black", "white")],
        "captures": [asdict(capture_stats(game, color)) for color in ("black", "white")],
        "events": [asdict(event) for event in move_events(game)],
        "indicators": [asdict(indicator) for indicator in timing_indicators(game)],
    }


def fetch_games(source: str, output_dir: Path, limit: int | None) -> tuple[int, int]:
    """Download game payloads as JSON into a directory, skipping cached files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    new = cached = 0
    for game_id in fetch_player_game_ids(source, limit):
        path = output_dir / f"game_{game_id}.json"
        if path.exists():
            cached += 1
            continue
        payload = fetch_game_json(str(game_id))
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        new += 1
    return new, cached


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "fetch":
            new, cached = fetch_games(args.source, args.output_dir, args.limit)
            print(f"{new} games fetched, {cached} cached in {args.output_dir}")
            return 0
        game = load_game(args.source)
        if args.command == "convert":
            sgf = to_sgf(game, annotate=args.annotate)
            if args.output:
                args.output.write_text(sgf + "\n", encoding="utf-8")
            else:
                print(sgf)
        elif args.command == "report":
            if args.json:
                print(json.dumps(report_payload(game), indent=2, ensure_ascii=False))
            else:
                print("\n".join(report_lines(game)))
        else:
            print("\n".join(info_lines(game)))
    except (GameDataError, requests.RequestException, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
