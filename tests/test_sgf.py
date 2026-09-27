"""SGF rendering: golden files, passes, handicap setup and escaping."""

from dataclasses import replace

import pytest

from pygo.sgf import sgf_point, sgf_result, to_sgf


def test_matches_golden(game_34508515, golden_34508515):
    assert to_sgf(game_34508515) + "\n" == golden_34508515


def test_matches_golden_handicap(game_40476992, golden_40476992):
    assert to_sgf(game_40476992) + "\n" == golden_40476992


def test_passes_are_empty_moves(game_34508515):
    sgf = to_sgf(game_34508515)
    assert ";W[]" in sgf
    assert ";B[]" in sgf
    assert "[zz]" not in sgf


def test_handicap_setup(game_40476992):
    lines = to_sgf(game_40476992).split("\n")
    assert "HA[3]" in lines
    assert "AB[pp][pd][dp]" in lines
    assert lines.index("AB[pp][pd][dp]") + 1 == lines.index(";W[cc]")


def test_rectangular_board_size(game_34508515):
    sgf = to_sgf(replace(game_34508515, board_width=19, board_height=9))
    assert "SZ[19:9]" in sgf


def test_no_handicap_tag_for_single_stone(game_34508515):
    assert "HA[" not in to_sgf(game_34508515)


def test_text_is_escaped(game_34508515):
    sgf = to_sgf(replace(game_34508515, name="a]b\\c"))
    assert "GN[a\\]b\\\\c]" in sgf


def test_annotate_flagged_moves(flagged_game):
    sgf = to_sgf(flagged_game, annotate=True)
    assert ";W[ee]C[window out of focus 5.0 s]" in sgf
    assert ";B[]C[SGF downloaded by user 7, 8; move edited after play]" in sgf
    plain = to_sgf(flagged_game)
    assert ";W[ee]\n" in plain
    assert ";B[]\n" in plain


def test_rules_labels(game_34508515):
    assert "RU[Japanese]" in to_sgf(game_34508515)
    assert "RU[AGA]" in to_sgf(replace(game_34508515, rules="aga"))
    assert "RU[New Zealand]" in to_sgf(replace(game_34508515, rules="nz"))
    assert "RU[Custom]" in to_sgf(replace(game_34508515, rules="custom"))


def test_sgf_point():
    assert sgf_point(16, 3) == "qd"
    assert sgf_point(2, 2) == "cc"


@pytest.mark.parametrize(
    ("outcome", "winner", "expected"),
    [
        ("17.5 points", "white", "W+17.5"),
        ("7.5 points", "black", "B+7.5"),
        ("Resignation", "white", "W+R"),
        ("Timeout", "black", "B+T"),
        ("draw", None, "0"),
        (None, None, None),
    ],
)
def test_sgf_result(outcome, winner, expected):
    assert sgf_result(outcome, winner) == expected
