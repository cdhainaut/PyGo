"""Shared fixtures: real OGS payloads trimmed to the keys py-go reads."""

import copy
import json
from pathlib import Path

import pytest

from pygo import Game

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> Game:
    payload = (FIXTURES / f"game_{name}.json").read_text(encoding="utf-8")
    return Game.from_ogs_json(json.loads(payload))


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def game_34508515() -> Game:
    """9x9 game with two passes and a points result."""
    return _load("34508515")


@pytest.fixture
def game_40476992() -> Game:
    """19x19 handicap game (3 stones) won by resignation."""
    return _load("40476992")


@pytest.fixture
def golden_34508515(fixtures_dir: Path) -> str:
    return (fixtures_dir / "game_34508515.sgf").read_text(encoding="utf-8")


@pytest.fixture
def golden_40476992(fixtures_dir: Path) -> str:
    return (fixtures_dir / "game_40476992.sgf").read_text(encoding="utf-8")


# Synthetic payload carrying the OGS fair-play extras (AdHocPackedMove tail).
FLAGGED_PAYLOAD = {
    "gamedata": {
        "game_id": 2,
        "game_name": "flagged",
        "players": {
            "black": {"id": 10, "username": "b"},
            "white": {"id": 20, "username": "w"},
        },
        "width": 9,
        "height": 9,
        "komi": 0.5,
        "rules": "japanese",
        "handicap": 0,
        "initial_player": "black",
        "initial_state": {"black": "", "white": ""},
        "moves": [
            [3, 3, 1000],
            [4, 4, 2500, 2, {"blur": 5000}],
            [-1, -1, 3000, 1, {"sgf_downloaded_by": [7, 8], "edited": True}],
            [5, 5, 4500, 1],
        ],
    }
}


@pytest.fixture
def flagged_payload() -> dict:
    return copy.deepcopy(FLAGGED_PAYLOAD)


@pytest.fixture
def flagged_game() -> Game:
    return Game.from_ogs_json(copy.deepcopy(FLAGGED_PAYLOAD))
