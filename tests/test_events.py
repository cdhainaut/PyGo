"""Fair-play events and think-time statistics."""

from dataclasses import replace

from pygo.events import move_events, time_summary, timing_indicators
from pygo.models import Move


def test_move_events(flagged_game):
    events = move_events(flagged_game)
    assert [(e.move_number, e.color, e.kind) for e in events] == [
        (2, "white", "blur"),
        (3, "black", "sgf_download"),
        (3, "black", "edited"),
    ]
    assert events[0].detail == "window out of focus 5.0 s"
    assert events[1].detail == "SGF downloaded by user 7, 8"


def test_no_events_on_plain_game(game_34508515):
    assert move_events(game_34508515) == []


def test_time_summary(flagged_game):
    black = time_summary(flagged_game, "black")
    assert black.timed_moves == 3
    assert black.total_s == 8.5
    assert black.mean_s == 2.833  # millisecond precision
    assert black.std_s == 1.434
    assert black.cv == 0.506
    assert black.median_s == 3.0
    assert black.blitz_share == 0.333
    assert black.max_s == 4.5
    assert black.slowest_move == 4
    white = time_summary(flagged_game, "white")
    assert (white.timed_moves, white.total_s, white.slowest_move) == (1, 2.5, 2)


def test_time_summary_without_moves(game_40476992):
    summary = time_summary(replace(game_40476992, moves=()), "black")
    assert (summary.timed_moves, summary.total_s, summary.slowest_move) == (0, 0.0, None)


def _with_times(game, times_ms):
    """Same game with synthetic think times, alternating black and white."""
    moves = tuple(Move(x=i % 9, y=i // 9, think_time_ms=t) for i, t in enumerate(times_ms))
    return replace(game, moves=moves)


def test_indicator_mechanical_cadence(flagged_game):
    game = _with_times(flagged_game, [5000] * 50)
    assert [(i.color, i.kind) for i in timing_indicators(game)] == [
        ("black", "mechanical_cadence"),
        ("white", "mechanical_cadence"),
    ]


def test_indicator_blitz_play(flagged_game):
    game = _with_times(flagged_game, [500] * 50)
    kinds = [(i.color, i.kind) for i in timing_indicators(game)]
    assert ("black", "blitz_play") in kinds
    assert ("white", "blitz_play") in kinds


def test_indicator_rhythm_shift(flagged_game):
    game = _with_times(flagged_game, [3000] * 25 + [10000] * 25)
    shifts = [i for i in timing_indicators(game) if i.kind == "rhythm_shift"]
    assert [i.color for i in shifts] == ["black", "white"]
    assert shifts[0].detail == "median think time 3 s -> 10 s from move 25"


def test_no_indicator_on_human_timing(flagged_game):
    times = [2500 + (i * 2654435761) % 7500 for i in range(52)]
    assert timing_indicators(_with_times(flagged_game, times)) == []
