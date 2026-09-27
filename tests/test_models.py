"""Parsing of OGS payloads into typed models."""

import pytest

from pygo.models import Game, GameDataError, Move, Player, Stone, ogs_rank_label


def test_game_metadata(game_34508515):
    game = game_34508515
    assert game.game_id == 34508515
    assert game.name == "sibusisongcobo606 vs. 바둑 사랑"
    assert game.black.name == "sibusisongcobo606"
    assert game.white.name == "바둑 사랑"
    assert (game.board_width, game.board_height) == (9, 9)
    assert game.komi == 3.5
    assert game.rules == "japanese"
    assert game.handicap == 1
    assert game.initial_player == "black"
    assert game.outcome == "17.5 points"
    assert game.winner == "white"
    assert game.start_time.date().isoformat() == "2021-06-14"
    assert game.source_url == "https://online-go.com/game/34508515"


def test_rank_labels(game_34508515):
    assert game_34508515.black.rank_label == "9k"
    assert game_34508515.white.rank_label == "8k"
    assert ogs_rank_label(29.02) == "1k"
    assert ogs_rank_label(30.0) == "1d"
    assert ogs_rank_label(31.2) == "2d"
    assert ogs_rank_label(38.2, professional=True) == "2p"
    assert Player(name="unknown").rank_label is None


def test_moves_and_passes(game_34508515):
    game = game_34508515
    assert len(game.moves) == 51
    assert (game.moves[0].x, game.moves[0].y) == (2, 5)
    assert game.moves[0].think_time_ms is not None
    assert Move(x=-1, y=-1).is_pass
    assert not Move(x=2, y=2).is_pass
    assert sum(move.is_pass for move in game.moves) == 2


def test_move_color_alternation(game_34508515, game_40476992):
    assert [game_34508515.move_color(i) for i in range(3)] == ["black", "white", "black"]
    assert [game_40476992.move_color(i) for i in range(3)] == ["white", "black", "white"]


def test_initial_stones(game_40476992):
    game = game_40476992
    assert game.handicap == 3
    assert game.initial_stones == (
        Stone(color="black", x=15, y=15),
        Stone(color="black", x=15, y=3),
        Stone(color="black", x=3, y=15),
    )


def test_empty_setup_is_no_stones(game_34508515):
    assert game_34508515.initial_stones == ()


def test_unfinished_game_has_no_result():
    game = Game.from_ogs_json(
        {
            "gamedata": {
                "game_id": 1,
                "players": {
                    "black": {"id": 10, "username": "b"},
                    "white": {"id": 20, "username": "w"},
                },
                "width": 19,
                "height": 19,
                "komi": 6.5,
                "rules": "chinese",
                "initial_player": "black",
                "initial_state": {"black": "", "white": ""},
                "moves": [[3, 3, 100], [-1, -1, 50], [15, 15, None, None, None]],
            }
        }
    )
    assert (game.outcome, game.winner) == (None, None)
    assert game.start_time is None
    assert [move.think_time_ms for move in game.moves] == [100, 50, None]
    assert game.moves[1].is_pass


@pytest.mark.parametrize(
    "payload",
    [{}, {"gamedata": {}}, {"gamedata": {"players": {"black": {}, "white": {}}}}],
)
def test_rejects_unknown_payloads(payload):
    with pytest.raises(GameDataError):
        Game.from_ogs_json(payload)


def test_rejects_unknown_winner():
    payload = {
        "gamedata": {
            "game_id": 1,
            "players": {
                "black": {"id": 10, "username": "b"},
                "white": {"id": 20, "username": "w"},
            },
            "width": 19,
            "height": 19,
            "komi": 6.5,
            "rules": "chinese",
            "initial_player": "black",
            "moves": [],
            "winner": 99,
        }
    }
    with pytest.raises(GameDataError):
        Game.from_ogs_json(payload)


def test_move_extras(flagged_game):
    blur_move = flagged_game.moves[1]
    assert blur_move.color == "white"
    assert blur_move.blur_ms == 5000
    assert not blur_move.edited
    pass_move = flagged_game.moves[2]
    assert pass_move.is_pass
    assert pass_move.sgf_downloaded_by == (7, 8)
    assert pass_move.edited
    assert flagged_game.moves[3].think_time_ms == 4500


def test_move_color_override(flagged_game):
    # move 4 is explicitly black although alternation would say white
    assert flagged_game.moves[3].color == "black"
    assert flagged_game.move_color(3) == "black"
