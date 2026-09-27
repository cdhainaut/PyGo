"""Thin client for the OGS REST API."""

from __future__ import annotations

import re
from typing import Iterator

import requests

from .config import OGS_API_URL, game_api_url
from .models import Game, GameDataError

_GAME_ID = re.compile(r"(?:online-go\.com/game/|^)(\d+)")


_PLAYER_URL = re.compile(r"online-go\.com/user/([\w-]+)")


def parse_game_id(source: str) -> int:
    """Game id from a bare id ("40476992") or an OGS game URL."""
    match = _GAME_ID.search(source.strip())
    if match is None:
        raise GameDataError(f"cannot read an OGS game id from {source!r}")
    return int(match.group(1))


def fetch_game_json(source: str) -> dict:
    """Download the raw OGS payload of a game by id or URL."""
    game_id = parse_game_id(source)
    response = requests.get(game_api_url(game_id), timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_game(source: str) -> Game:
    """Download an OGS game by id or URL and parse it."""
    return Game.from_ogs_json(fetch_game_json(source))


def resolve_player_id(source: str) -> int:
    """Player id from a numeric id, an OGS user URL, or a username."""
    text = source.strip()
    if text.isdigit():
        return int(text)
    match = _PLAYER_URL.search(text)
    username = match.group(1) if match else text
    response = requests.get(f"{OGS_API_URL}/players", params={"username": username}, timeout=30)
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        raise GameDataError(f"OGS player {username!r} not found")
    return int(results[0]["id"])


def fetch_player_game_ids(source: str, limit: int | None = None) -> Iterator[int]:
    """Game ids of a player, most recent finished game first."""
    player_id = resolve_player_id(source)
    url = f"{OGS_API_URL}/players/{player_id}/games"
    params: dict | None = {"ordering": "-ended", "ended__isnull": "false", "page_size": 100}
    yielded = 0
    while url:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        page = response.json()
        for entry in page["results"]:
            yield int(entry["id"])
            yielded += 1
            if limit is not None and yielded >= limit:
                return
        url = page.get("next")
        params = None  # the next URL already carries the query
