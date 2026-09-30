# py-go

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

`py-go` reads a game from [Online-Go](https://online-go.com) and writes SGF that scripts can work
with. It also reports think time and captures, plus a few fair-play signals.

The OGS API hands out game records as JSON. Its SGF export wraps every move in a new variation:

```sgf
(;FF[4] ... ;W[cc](;B[jd](;W[qf](;B[nc] ... )))))))
```

That is fine in a viewer and annoying in a script. `py-go` writes the same game as a flat tree.
Along the way it fixes what breaks tooling: passes (OGS sends `[-1, -1]`, and a naive conversion
writes a stone on `zz`), handicap stones (grouped as `AB[pp][pd][dp]`), and rectangular boards
(`SZ[19:9]`).

The output was checked move by move against the native OGS export on real games, handicap and
passes included. Capture counts were cross-checked against `sgfmill`'s board replay.

## Install

```bash
git clone https://github.com/cdhainaut/PyGo.git
cd PyGo && pip install -e .
```

Python 3.11+, one dependency (`requests`). Not on PyPI yet.

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

$ py-go report 37044914 --json
$ py-go convert 37044914 --clipboard
$ py-go convert https://online-go.com/game/37044914 -o game.sgf
$ py-go convert 37044914 --annotate
$ py-go convert 37044914
$ py-go convert saved_game.json
$ py-go fetch triple_atari -o games/ --limit 50
```

`source` is an OGS game URL, a bare game id, or a path to a saved game JSON. `convert` writes to
stdout unless `-o` is given; `--clipboard` copies the SGF instead, ready to paste into a viewer such
as KaTrain (it uses `wl-copy`, `xclip`, `xsel` or `pbcopy`, whichever is installed). `--annotate`
adds `C[]` comments on flagged moves. `report --json` prints the same content as JSON. `fetch` takes
a player id, a username or a user URL, and skips games already in the target directory.

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

`Game`, `Player`, `Move` and `Stone` are frozen dataclasses. `Move` carries `think_time_ms`,
`is_pass`, and the OGS extras `blur_ms`, `sgf_downloaded_by` and `edited`. `pygo.board` replays a
game and counts captures. `pygo.events` turns think times into statistics and fair-play events.

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

One node per move, all metadata in the root node.

## Conventions

| OGS JSON | py-go / SGF |
|---|---|
| `moves`: `[x, y, think_time_ms]`, 0-based from the top-left corner | point `[col][row]`, letters `a..s` (`i` included) |
| pass encoded as `[-1, -1]` | empty move `;B[]` |
| `initial_state`: `"pppddp"` concatenated points | `AB[pp][pd][dp]` |
| `rank`: float, 30 = 1 dan | `BR`/`WR` label: `ceil(30 - rank)` kyu, `floor(rank - 29)` dan |
| `outcome`: `"17.5 points"`, `"Resignation"`, `"Timeout"` | `RE`: `W+17.5`, `W+R`, `W+T` |
| 5th move element: `{"blur", "sgf_downloaded_by", "edited"}` | `GameEvent`s, `C[]` comments with `--annotate` |

Points are counted from the top left and use `a..s` including `i`, unlike the usual OGS display
(columns A to T without I, rows 1 to 19 from the bottom). `py-go` keeps the SGF convention
everywhere and never mixes the two.

Ranks are floats where 30 means 1 dan; the label formulas are in the table. `blur` is the longest
stretch in ms that the player had the window unfocused while it was their turn, recorded by the OGS
client as an anti-cheat metric. Both extras are marked "typically restricted" by OGS, and most
public payloads carry none: I scanned 30 random games and found zero. Missing extras are normal.

## Fair-play indicators

`py-go report` derives hints from think times alone: cadence regularity (`cv`), the share of moves
played under 2 s, and whether the median shifts by a factor of 3 between the halves of the game.
Treat them as hints rather than proof. People blitz, and engine assistance does not have to leave
a trace in the timing.

Agreement with an engine is the signal that counts, and it needs an engine run of your own. OGS
computes something along those lines server-side, but `/ai_reviews` returns only a summary; the
per-move data is not in the REST API. Importing an external KataGo or KaTrain analysis is planned.

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

Tests run offline on trimmed OGS payloads in `tests/fixtures/`, each with the expected SGF frozen
as a golden file.

## Roadmap

- import an external KataGo analysis and cross it with think-time spikes
- rating integrity over a `py-go fetch` dataset: win rate against rank difference, short resignations
- opening repertoire and score-margin statistics
- territory estimates

## License

MIT, see [LICENSE](LICENSE).
