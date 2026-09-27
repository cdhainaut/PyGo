"""CLI: conversion to file or stdout, game summary, error reporting."""

import json

from pygo.cli import main
from pygo.sgf import to_sgf


def test_convert_to_file(tmp_path, fixtures_dir, game_34508515, golden_34508515):
    output = tmp_path / "game.sgf"
    source = str(fixtures_dir / "game_34508515.json")
    assert main(["convert", source, "-o", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == golden_34508515
    assert output.read_text(encoding="utf-8") == to_sgf(game_34508515) + "\n"


def test_convert_to_stdout(capsys, fixtures_dir, golden_34508515):
    source = str(fixtures_dir / "game_34508515.json")
    assert main(["convert", source]) == 0
    assert capsys.readouterr().out == golden_34508515


def test_info(capsys, fixtures_dir):
    source = str(fixtures_dir / "game_34508515.json")
    assert main(["info", source]) == 0
    out = capsys.readouterr().out
    assert "sibusisongcobo606 (9k) vs. 바둑 사랑 (8k)" in out
    assert "2021-06-14 | 9x9 | japanese rules | komi 3.5" in out
    assert "result W+17.5 | 51 moves (2 passes)" in out
    assert "https://online-go.com/game/34508515" in out


def test_info_handicap(capsys, fixtures_dir):
    source = str(fixtures_dir / "game_40476992.json")
    assert main(["info", source]) == 0
    out = capsys.readouterr().out
    assert "handicap 3" in out
    assert "3 setup stones" in out


def test_unknown_source_reports_error(capsys):
    assert main(["convert", "not-a-game"]) == 1
    assert "error:" in capsys.readouterr().err


def test_convert_annotate(tmp_path, flagged_payload):
    source = tmp_path / "flagged.json"
    source.write_text(json.dumps(flagged_payload), encoding="utf-8")
    output = tmp_path / "flagged.sgf"
    assert main(["convert", str(source), "-o", str(output), "--annotate"]) == 0
    sgf = output.read_text(encoding="utf-8")
    assert ";W[ee]C[window out of focus 5.0 s]" in sgf


def test_report_text(capsys, tmp_path, flagged_payload):
    source = tmp_path / "flagged.json"
    source.write_text(json.dumps(flagged_payload), encoding="utf-8")
    assert main(["report", str(source)]) == 0
    out = capsys.readouterr().out
    assert "Think time" in out
    assert "black: 3 moves" in out
    assert "| mean 2.8 s | median 3.0 s | max 4.5 s (move 4)" in out
    assert "Events (3)" in out
    assert "move 2 (white): window out of focus 5.0 s" in out
    assert "Indicators (0)" in out


def test_report_captures(capsys, fixtures_dir):
    source = str(fixtures_dir / "game_34508515.json")
    assert main(["report", source]) == 0
    out = capsys.readouterr().out
    assert "Captures" in out
    assert "white: 6 stones in 2 moves | first move 46 | largest 5 (move 48)" in out
    assert "black: 1 stone in 1 move | first move 49 | largest 1 (move 49)" in out


def test_report_json(capsys, tmp_path, flagged_payload):
    source = tmp_path / "flagged.json"
    source.write_text(json.dumps(flagged_payload), encoding="utf-8")
    assert main(["report", str(source), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["game"]["id"] == 2
    assert payload["game"]["result"] is None
    assert [row["total_s"] for row in payload["think_time"]] == [8.5, 2.5]
    assert [row["stones"] for row in payload["captures"]] == [0, 0]
    assert payload["indicators"] == []
    assert [event["kind"] for event in payload["events"]] == ["blur", "sgf_download", "edited"]


def test_fetch_games_caches(tmp_path, monkeypatch, capsys):
    payloads = {1: {"gamedata": {"game_id": 1}}, 2: {"gamedata": {"game_id": 2}}}
    fetched = []

    def fake_fetch_game_json(game_id):
        fetched.append(game_id)
        return payloads[int(game_id)]

    monkeypatch.setattr("pygo.cli.fetch_player_game_ids", lambda source, limit: iter([1, 2]))
    monkeypatch.setattr("pygo.cli.fetch_game_json", fake_fetch_game_json)
    output_dir = tmp_path / "games"

    assert main(["fetch", "7", "-o", str(output_dir), "--limit", "2"]) == 0
    assert sorted(path.name for path in output_dir.iterdir()) == ["game_1.json", "game_2.json"]
    assert fetched == ["1", "2"]
    assert "2 games fetched, 0 cached" in capsys.readouterr().out

    assert main(["fetch", "7", "-o", str(output_dir), "--limit", "2"]) == 0
    assert fetched == ["1", "2"]  # cached files are not downloaded again
    assert "0 games fetched, 2 cached" in capsys.readouterr().out
