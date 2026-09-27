# py-go

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

Convert and inspect [Online-Go](https://online-go.com) games as clean SGF — from the command line or from Python.

`py-go` downloads the JSON payload of an OGS game and rebuilds a flat, complete SGF record: full
metadata, handicap setup and one node per move. It also gives typed access to the move list, player
ranks, per-move think time and capture statistics for downstream analysis.

## Why

OGS keeps every game in its own JSON format (`/api/v1/games/<id>`), and its native SGF export wraps
every move in a nested variation:

```sgf
(;FF[4] ... ;W[cc](;B[jd](;W[qf](;B[nc] ... )))))))
```

Fine for a viewer, painful for scripts. `py-go` renders the same game as a flat tree with complete
metadata, and fixes the details that break downstream tools: passes become real empty moves
(`;B[]`, not a stone on `zz`), handicap stones are grouped in `AB[...]`, rectangular boards and
non-square sizes are supported.

Output is verified against the native OGS export: identical move sequences and metadata on handicap,
pass, points and resignation games.

## Install

```bash
git clone https://github.com/carlitador/PyGo.git
cd PyGo && pip install -e .
```

Requires Python 3.11+ and `requests`. Not published on PyPI yet.

## Command line

```console
$ py-go info 37044914
Game 37044914: NewHand2020 (6k) vs. Changsha (6k)
2021-09-15 | 19x19 | japanese rules | komi 6.5
result B+7.5 | 301 moves (2 passes)
https://online-go.com/game/37044914

$ py-go report 37044914
Game 37044914: NewHand2020 (6k) vs. Changsha (6k)
...

Think time
  black: 151 moves | total 817 s | mean 5.4 s | median 2.9 s | max 46.3 s (move 281) | cv 1.26 | blitz 32%
  white: 150 moves | total 760 s | mean 5.1 s | median 2.1 s | max 73.1 s (move 282) | cv 1.89 | blitz 49%

Captures
  black: 17 stones in 14 moves | first move 35 | largest 3 (move 287)
  white: 17 stones in 11 moves | first move 38 | largest 5 (move 272)

Events (0)
  none

Indicators (0)
  none

$ py-go report 37044914 --json            # machine-readable report
$ py-go convert https://online-go.com/game/37044914 -o game.sgf
$ py-go convert 37044914 --annotate      # flagged moves get C[] comments
$ py-go convert 37044914                 # SGF on stdout
$ py-go convert saved_game.json          # works offline on a saved payload
$ py-go fetch triple_atari -o games/ --limit 50   # games of a player as JSON, with cache
```

`source` is an OGS game URL, a bare game id, or the path of a saved game JSON. `fetch` takes a
player id, a username or an OGS user URL, and skips games already saved in the target directory.

## Python API

```python
from pygo import fetch_game, to_sgf
from pygo.board import capture_counts, capture_stats
from pygo.events import move_events, time_summary

game = fetch_game("37044914")
print(game.black.name, game.black.rank_label, "vs.", game.white.name)
print(to_sgf(game, annotate=True))
print(time_summary(game, "black"), capture_stats(game, "black"))
print(move_events(game), capture_counts(game))
```

- `Game` — metadata, setup stones and moves; `player(color)`, `move_color(i)`, `source_url`
- `Move` — `x`, `y`, `think_time_ms`, `is_pass`, plus the OGS fair-play extras `blur_ms`,
  `sgf_downloaded_by`, `edited` and the `color` override of edited games
- `Player` — `name`, `rank` (OGS scale), `rank_label` (`"9k"`, `"4d"`, `"9p"`)
- `board.Board` — replay with capture detection; `capture_counts(game)`, `capture_stats(game, color)`
- `events.move_events(game)` — flagged moves as `GameEvent`s; `events.time_summary(game, color)` —
  think-time statistics as a `TimeSummary` (mean, std, cv, blitz share, median, max)
- `events.timing_indicators(game)` — descriptive fair-play indicators as `Indicator`s
- `Stone`, `GameDataError`, `fetch_game`, `to_sgf`

## SGF output

```sgf
(;
FF[4]
CA[UTF-8]
GM[1]
DT[2022-01-18]
PC[OGS: https://online-go.com/game/40476992]
GN[Partie amicale]
PB[triple_atari]
PW[Ka35]
BR[8k]
WR[5k]
RE[W+R]
SZ[19]
KM[0.5]
RU[Japanese]
HA[3]
AB[pp][pd][dp]
;W[cc]
;B[jd]
)
```

## Conventions

| OGS JSON | py-go / SGF |
|---|---|
| `moves`: `[x, y, think_time_ms]`, 0-based from the top-left corner | point `[col][row]`, letters `a..s` (`i` included) |
| pass encoded as `[-1, -1]` | empty move `;B[]` |
| `initial_state`: `"pppddp"` concatenated points | `AB[pp][pd][dp]` |
| `rank`: float, 30 = 1 dan | `BR`/`WR` label: `ceil(30 - rank)` kyu, `floor(rank - 29)` dan |
| `outcome`: `"17.5 points"`, `"Resignation"`, `"Timeout"` | `RE`: `W+17.5`, `W+R`, `W+T` |
| 5th move element: `{"blur", "sgf_downloaded_by", "edited"}` | `GameEvent`s, `C[]` comments with `--annotate` |

`blur` is the maximum time (ms) the player had the window unfocused while it was their turn,
reported by the OGS client as an anti-cheat metric. Both extras are marked "typically restricted
information" by OGS: they are absent from most public payloads, which is not an error.

Note the difference with the usual OGS display convention (columns A–T without I, rows 1–19 from the
bottom): `py-go` follows the SGF convention and keeps it everywhere.

## Project layout

```text
pygo/
├── models.py   # dataclasses: Game, Player, Move, Stone + OGS payload parsing
├── board.py    # board replay, capture detection and statistics
├── events.py   # fair-play events and think-time statistics
├── ogs.py      # OGS REST client
├── sgf.py      # SGF writer
├── cli.py      # py-go convert / info / report / fetch
└── config.py   # endpoints and URLs
tests/          # one file per module, real game fixtures with golden SGF
```

## Development

```bash
pip install -e .[dev]
pytest
ruff check . && ruff format --check .
```

Tests run offline on trimmed OGS payloads kept in `tests/fixtures/`, each with the expected SGF
frozen as a golden file.

## Fair-play indicators

`py-go report` derives review hints from think times alone: cadence regularity (`cv`, low means
mechanical), blitz share (moves faster than 2 s), and rhythm shift (median ratio between game
halves). They are **signals to review, never proof of cheating**: humans can blitz, and engines can
be consulted without them. The strongest signal — agreement with a Go engine — requires an engine
analysis, which OGS does not expose publicly (its `/ai_reviews` endpoint only returns summary
metadata, verified). Importing an external KataGo/katrain analysis is on the roadmap.

## Roadmap

- **Engine agreement** — import a bring-your-own KataGo analysis (win-rate loss, top-choice
  agreement) and cross it with think-time spikes: the classic selective-assistance signature
- **Rating integrity** — over a `py-go fetch` dataset: win rate vs rank difference, short-game
  resignation patterns (sandbagging), rated/unrated splits
- **Game statistics** — opening repertoire, score margins, game-length distributions
- **Territory estimates** — coarse endgame position evaluation

## License

GPL-3.0 — see [LICENSE](LICENSE).
