# Changelog

## [0.1.0] - 2026-09-27

First release of `py-go`, a rewrite of the PyGo prototype into an installable package.

### Added

- OGS game payloads parsed into typed models (`Game`, `Player`, `Move`, `Stone`)
- SGF writer: flat tree, complete metadata (`DT/PC/GN/PB/PW/BR/WR/RE/SZ/KM/RU/HA`),
  handicap setup, rectangular boards, proper empty moves for passes
- Think-time statistics (mean, std, cadence regularity, blitz share) and descriptive
  fair-play indicators (mechanical cadence, blitz play, rhythm shift)
- Fair-play move events (`blur`, mid-game SGF downloads, move edits) with optional
  `C[]` annotations in the exported SGF
- Board replay with capture detection and capture statistics
- OGS REST client: game fetch by id or URL, player game listing with pagination
- CLI: `py-go convert`, `py-go info`, `py-go report`, `py-go fetch`
- Test suite (65 tests) with real game fixtures and golden SGF files, validated
  against the native OGS SGF export and an independent board replay (sgfmill)
- MIT license

### Fixed (vs the prototype)

- passes were written as stones on `zz` instead of empty moves (`;B[]`)
- metadata was limited to `GM/SZ/KM`, and `SZ` ignored rectangular boards
- undeclared runtime dependencies, no tests, no packaging metadata
