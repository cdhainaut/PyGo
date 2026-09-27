"""Fair-play events, think-time statistics and timing indicators."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Literal

from .models import Color, Game

EventKind = Literal["blur", "sgf_download", "edited"]
IndicatorKind = Literal["mechanical_cadence", "blitz_play", "rhythm_shift"]

BLITZ_TIME_S = 2.0  # a move played faster than this is a blitz move
BLITZ_SHARE_LIMIT = 0.5  # share of blitz moves that raises an indicator
MECHANICAL_CV = 0.3  # think-time coefficient of variation below this is mechanical
RHYTHM_RATIO = 3.0  # median ratio between game halves that marks a rhythm shift
MIN_PROFILE_MOVES = 20  # timed moves per player before indicators are computed


@dataclass(frozen=True)
class GameEvent:
    """One flagged move, from the OGS fair-play extras."""

    move_number: int  # 1-based
    color: Color
    kind: EventKind
    detail: str


@dataclass(frozen=True)
class Indicator:
    """A descriptive timing signal worth reviewing. A signal, not a proof."""

    color: Color
    kind: IndicatorKind
    detail: str


@dataclass(frozen=True)
class TimeSummary:
    """Think-time statistics of one player over the moves they played."""

    color: Color
    timed_moves: int
    total_s: float
    mean_s: float
    std_s: float
    cv: float  # std_s / mean_s: cadence regularity, low means mechanical
    median_s: float
    blitz_share: float  # share of moves faster than BLITZ_TIME_S
    max_s: float
    slowest_move: int | None  # 1-based


def move_events(game: Game) -> list[GameEvent]:
    """Flagged moves of a game, in move order."""
    events = []
    for index, move in enumerate(game.moves):
        number, color = index + 1, game.move_color(index)
        if move.blur_ms:
            blur_s = move.blur_ms / 1000
            events.append(GameEvent(number, color, "blur", f"window out of focus {blur_s:.1f} s"))
        if move.sgf_downloaded_by:
            users = ", ".join(str(user) for user in move.sgf_downloaded_by)
            events.append(
                GameEvent(number, color, "sgf_download", f"SGF downloaded by user {users}")
            )
        if move.edited:
            events.append(GameEvent(number, color, "edited", "move edited after play"))
    return events


def time_summary(game: Game, color: Color) -> TimeSummary:
    """Think-time statistics for one color; zeros when no move carries a time."""
    timed = [
        (index, move.think_time_ms)
        for index, move in enumerate(game.moves)
        if move.think_time_ms is not None and game.move_color(index) == color
    ]
    if not timed:
        return TimeSummary(color, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None)
    times_ms = [think_time for _, think_time in timed]
    slowest_move = max(timed, key=lambda item: item[1])[0] + 1
    mean_s = statistics.mean(times_ms) / 1000
    std_s = statistics.pstdev(times_ms) / 1000
    return TimeSummary(
        color=color,
        timed_moves=len(timed),
        total_s=round(sum(times_ms) / 1000, 3),
        mean_s=round(mean_s, 3),
        std_s=round(std_s, 3),
        cv=round(std_s / mean_s, 3) if mean_s else 0.0,
        median_s=round(statistics.median(times_ms) / 1000, 3),
        blitz_share=round(sum(t < BLITZ_TIME_S * 1000 for t in times_ms) / len(times_ms), 3),
        max_s=round(max(times_ms) / 1000, 3),
        slowest_move=slowest_move,
    )


def timing_indicators(game: Game) -> list[Indicator]:
    """Descriptive timing signals per player: cadence, blitz play, rhythm shift.

    These are review hints from think times alone, never proof of cheating.
    """
    indicators = []
    for color in ("black", "white"):
        summary = time_summary(game, color)
        if summary.timed_moves < MIN_PROFILE_MOVES:
            continue
        if summary.cv < MECHANICAL_CV:
            detail = f"steady cadence (cv {summary.cv:.2f}) on {summary.timed_moves} moves"
            indicators.append(Indicator(color, "mechanical_cadence", detail))
        if summary.blitz_share > BLITZ_SHARE_LIMIT:
            detail = f"{summary.blitz_share:.0%} of moves faster than {BLITZ_TIME_S:g} s"
            indicators.append(Indicator(color, "blitz_play", detail))
        shift = _rhythm_shift(game, color)
        if shift is not None:
            move_number, before_s, after_s = shift
            detail = f"median think time {before_s:g} s -> {after_s:g} s from move {move_number}"
            indicators.append(Indicator(color, "rhythm_shift", detail))
    return indicators


def _rhythm_shift(game: Game, color: Color) -> tuple[int, float, float] | None:
    """Chronological half split of one player's think times, None when stable."""
    timed = [
        (index + 1, move.think_time_ms / 1000)
        for index, move in enumerate(game.moves)
        if move.think_time_ms is not None and game.move_color(index) == color
    ]
    half = len(timed) // 2
    if half < MIN_PROFILE_MOVES // 2:
        return None
    before = statistics.median(seconds for _, seconds in timed[:half])
    after = statistics.median(seconds for _, seconds in timed[half:])
    ratio = max(before, after) / min(before, after) if min(before, after) > 0 else 0.0
    if ratio < RHYTHM_RATIO:
        return None
    return timed[half][0], round(before, 3), round(after, 3)
