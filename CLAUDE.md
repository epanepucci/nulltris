# Nulltris

A falling-block puzzle game written in Python using pygame-ce. Single file: `main.py`.

## Run

```
uv run python main.py
```

## Controls

| Key | Action |
|-----|--------|
| ← / → | Move |
| ↑ or X | Rotate counter-clockwise |
| Z / Ctrl | Rotate clockwise |
| ↓ | Soft drop |
| Space | Hard drop |
| C / Shift | Hold piece |
| P | Pause |
| R | Restart |
| Esc | Open/close settings |
| Ctrl+Q | Quit immediately |

## Architecture

Everything lives in `main.py`. No external game framework beyond pygame-ce.

### Key classes

**`Settings`** — plain object holding all user preferences. Persisted to `~/.nulltris_settings.json` (saved on quit and when the settings overlay is closed).

**`Game`** — all game logic. Board is a `ROWS×COLS` list of `None | RGB tuple`. Pieces are locked by writing their color into the board. Public interface used by `main()`:
- `_reset(garbage_rows)` — restart, optionally pre-filling the bottom N rows with garbage
- `move(dc)`, `rotate(direction)`, `soft_drop()`, `hard_drop()`, `hold()`
- `mutate()` — change the falling piece to a random different type (subject to constraints)
- `update(dt_ms)` — advance gravity and lock timer; call once per frame
- `ghost_row()` — row where the current piece would land

**`Piece`** — holds kind, pre-computed 4-rotation matrices, current `row`/`col`/`rot`. Spawn row is 0 for all pieces except I (spawns at -1).

**`DAS`** — delayed auto-shift for held left/right keys. `DAS_DELAY = 300 ms`, `DAS_REPEAT = 50 ms`.

### Layout system

All pixel positions are computed dynamically in `compute_layout(win_w, win_h)`, which returns a `SimpleNamespace`. Cell size maximises to fill the available height, constrained so the panel (minimum `MIN_PANEL_W = 130 px`) always fits. On `WINDOWRESIZED`, layout and fonts are recomputed. Window size and position are restored on next launch via `SDL_VIDEO_WINDOW_POS` env var (set before `set_mode`, then cleared).

Fonts scale with cell size (`make_fonts(cell)`), recreated on each resize.

### Rotation

Uses standard wall-kick offset tables (`_KICKS_JLSTZ` and `_KICKS_I`), keyed by `(from_rot, to_rot)`. Default key binding rotates **counter-clockwise**; Z/Ctrl rotates clockwise.

### Piece randomiser

7-bag: a shuffled copy of all 7 piece types is consumed before reshuffling. The internal queue always buffers `MAX_PREVIEW = 6` pieces; the panel displays only `settings.preview_count` of them (0–6).

### Scoring

| Lines cleared | Base points |
|---------------|-------------|
| 1 | 100 |
| 2 | 300 |
| 3 | 500 |
| 4 (Nulltris) | 800 |

Base × current level. Soft drop: +1/row. Hard drop: +2/row.

Level increases every 10 lines. Gravity speed follows a 20-entry table (`_GRAVITY`), capped at level 20.

## Settings

Opened with Esc. Navigate with ↑↓, change with ←→, close with Esc or Enter. Saved on close.

| Setting | Default | Notes |
|---------|---------|-------|
| Preview pieces | 3 | 0–6 next pieces shown in panel |
| Landing shadow | ON | Ghost piece showing where current piece lands |
| Garbage rows | 0 | 0–15 pre-filled rows at start; takes effect on restart (R) |
| Auto-mutate | OFF | See below |

### Auto-mutate

When ON, the game schedules a single random mutation attempt per piece, firing 400–1800 ms after spawn. At that moment, `mutate()` is called:

- **Height guard**: the piece's lowest cell must be more than 4 rows above the topmost locked cell. Panel indicator turns amber when budget is available but height condition isn't met.
- **Budget**: at most 2 mutations per rolling 10-piece window. Counter resets automatically.
- On a successful mutation the piece changes to a random different type (column-adjusted by up to ±3 to fit). Lock timer resets.

Panel shows a `●●` / `●○` / `○○` indicator (green / amber / dim) while auto-mutate is on.

## File layout

```
main.py          — entire game
pyproject.toml   — project metadata, declares pygame-ce dependency
uv.lock          — locked dependency versions
CLAUDE.md        — this file
```

Settings file: `~/.nulltris_settings.json`
