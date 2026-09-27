"""OGS client wiring: game id parsing and fetch, without network."""

import json

import pytest

from pygo.models import GameDataError
from pygo.ogs import (
    fetch_game,
    fetch_game_json,
    fetch_player_game_ids,
    parse_game_id,
    resolve_player_id,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("40476992", 40476992),
        ("https://online-go.com/game/40476992", 40476992),
        ("online-go.com/game/40476992/", 40476992),
        ("https://online-go.com/game/40476992/review/123", 40476992),
    ],
)
def test_parse_game_id(source, expected):
    assert parse_game_id(source) == expected


@pytest.mark.parametrize("source", ["", "not-a-game", "https://example.com/40476992"])
def test_parse_game_id_rejects_unknown(source):
    with pytest.raises(GameDataError):
        parse_game_id(source)


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_fetch_game_without_network(monkeypatch, fixtures_dir):
    payload = json.loads((fixtures_dir / "game_34508515.json").read_text(encoding="utf-8"))
    monkeypatch.setattr("pygo.ogs.requests.get", lambda url, timeout: _Response(payload))
    assert fetch_game_json("34508515") == payload
    assert fetch_game("34508515").game_id == 34508515


def test_resolve_player_id(monkeypatch):
    monkeypatch.setattr(
        "pygo.ogs.requests.get",
        lambda url, params=None, timeout=None: _Response({"results": [{"id": 1104163}]}),
    )
    assert resolve_player_id("triple_atari") == 1104163
    assert resolve_player_id("https://online-go.com/user/triple_atari") == 1104163
    assert resolve_player_id("1104163") == 1104163


def test_resolve_player_id_unknown(monkeypatch):
    monkeypatch.setattr(
        "pygo.ogs.requests.get",
        lambda url, params=None, timeout=None: _Response({"results": []}),
    )
    with pytest.raises(GameDataError):
        resolve_player_id("ghost")


def test_fetch_player_game_ids_paginates(monkeypatch):
    pages = {
        "https://online-go.com/api/v1/players/7/games": {
            "results": [{"id": 1}, {"id": 2}],
            "next": "https://online-go.com/api/v1/players/7/games?page=2",
        },
        "https://online-go.com/api/v1/players/7/games?page=2": {
            "results": [{"id": 3}],
            "next": None,
        },
    }

    def fake_get(url, params=None, timeout=None):
        return _Response(pages[url])

    monkeypatch.setattr("pygo.ogs.requests.get", fake_get)
    assert list(fetch_player_game_ids("7")) == [1, 2, 3]
    assert list(fetch_player_game_ids("7", limit=2)) == [1, 2]
