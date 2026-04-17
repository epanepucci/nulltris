import json
import os
import pygame
import random
import sys
from pathlib import Path
from types import SimpleNamespace

# ── Fixed constants ────────────────────────────────────────
COLS, ROWS   = 10, 20
MARGIN       = 20
MIN_PANEL_W  = 130
MAX_PREVIEW  = 6

FPS         = 60
LOCK_DELAY  = 500
DAS_DELAY   = 300
DAS_REPEAT  = 50
SOFT_FACTOR = 20

INIT_W, INIT_H  = 550, 640
MAX_GARBAGE     = 15
SETTINGS_FILE   = Path.home() / ".nulltris_settings.json"

# ── Colors ─────────────────────────────────────────────────
BG      = ( 12,  12,  18)
GRID_C  = ( 28,  28,  38)
BORDER  = ( 60,  60,  80)
WHITE   = (255, 255, 255)
GRAY    = (130, 130, 145)
DARK    = ( 35,  35,  48)
GHOST   = ( 60,  60,  75)
GARBAGE = ( 85,  88,  98)
OVERLAY = ( 20,  20,  30)
HILITE  = ( 50,  80, 140)

COLORS = {
    'I': (  0, 210, 220),
    'O': (230, 210,   0),
    'T': (180,   0, 220),
    'S': ( 50, 210,  50),
    'Z': (220,  50,  50),
    'J': ( 30,  80, 220),
    'L': (220, 140,   0),
}

# ── Piece shapes ───────────────────────────────────────────
SHAPES = {
    'I': [[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]],
    'O': [[1,1],[1,1]],
    'T': [[0,1,0],[1,1,1],[0,0,0]],
    'S': [[0,1,1],[1,1,0],[0,0,0]],
    'Z': [[1,1,0],[0,1,1],[0,0,0]],
    'J': [[1,0,0],[1,1,1],[0,0,0]],
    'L': [[0,0,1],[1,1,1],[0,0,0]],
}

PIECE_TYPES = list(SHAPES.keys())

_KICKS_JLSTZ = {
    (0,1):[(-1,0),(-1,-1),(0,2),(-1,2)],
    (1,0):[(1,0),(1,1),(0,-2),(1,-2)],
    (1,2):[(1,0),(1,1),(0,-2),(1,-2)],
    (2,1):[(-1,0),(-1,-1),(0,2),(-1,2)],
    (2,3):[(1,0),(1,-1),(0,2),(1,2)],
    (3,2):[(-1,0),(-1,1),(0,-2),(-1,-2)],
    (3,0):[(-1,0),(-1,1),(0,-2),(-1,-2)],
    (0,3):[(1,0),(1,-1),(0,2),(1,2)],
}
_KICKS_I = {
    (0,1):[(-2,0),(1,0),(-2,-1),(1,2)],
    (1,0):[(2,0),(-1,0),(2,1),(-1,-2)],
    (1,2):[(-1,0),(2,0),(-1,2),(2,-1)],
    (2,1):[(1,0),(-2,0),(1,-2),(-2,1)],
    (2,3):[(2,0),(-1,0),(2,1),(-1,-2)],
    (3,2):[(-2,0),(1,0),(-2,-1),(1,2)],
    (3,0):[(1,0),(-2,0),(1,-2),(-2,1)],
    (0,3):[(-1,0),(2,0),(-1,2),(2,-1)],
}

_GRAVITY = [800,720,630,550,470,380,300,220,130,100,
             83, 83, 83, 67, 67, 67, 50, 50, 50, 33]

SCORE_TABLE = {1: 100, 2: 300, 3: 500, 4: 800}


# ── Dynamic layout ─────────────────────────────────────────

def compute_layout(win_w, win_h):
    max_by_h = (win_h - 2 * MARGIN) // ROWS
    max_by_w = (win_w - MIN_PANEL_W - 3 * MARGIN) // COLS
    cell = max(10, min(max_by_h, max_by_w))
    board_w = COLS * cell
    board_h = ROWS * cell
    board_x = MARGIN
    board_y = (win_h - board_h) // 2
    panel_x = board_x + board_w + MARGIN
    panel_w = win_w - panel_x - MARGIN
    return SimpleNamespace(
        cell=cell,
        board_x=board_x, board_y=board_y,
        board_w=board_w, board_h=board_h,
        panel_x=panel_x, panel_w=panel_w,
        win_w=win_w, win_h=win_h,
    )


def make_fonts(cell):
    return (
        pygame.font.SysFont("monospace", max(12, int(cell * 0.80)), bold=True),
        pygame.font.SysFont("monospace", max(10, int(cell * 0.60)), bold=True),
        pygame.font.SysFont("monospace", max( 8, int(cell * 0.43))),
    )


# ── Settings ───────────────────────────────────────────────

class Settings:
    def __init__(self):
        self.preview_count = 3
        self.show_ghost    = True
        self.garbage_rows  = 0
        self.auto_mutate   = False
        self.teleport      = False
        self.win_w         = INIT_W
        self.win_h         = INIT_H
        self.win_x         = None   # None → let the OS pick
        self.win_y         = None


def load_settings():
    s = Settings()
    try:
        data = json.loads(SETTINGS_FILE.read_text())
        s.preview_count = max(0, min(MAX_PREVIEW, int(data.get("preview_count", s.preview_count))))
        s.show_ghost    = bool(data.get("show_ghost",   s.show_ghost))
        s.garbage_rows  = max(0, min(MAX_GARBAGE, int(data.get("garbage_rows",  s.garbage_rows))))
        s.auto_mutate   = bool(data.get("auto_mutate",  s.auto_mutate))
        s.teleport      = bool(data.get("teleport",     s.teleport))
        s.win_w         = max(300, int(data.get("win_w", s.win_w)))
        s.win_h         = max(300, int(data.get("win_h", s.win_h)))
        if "win_x" in data and "win_y" in data:
            s.win_x = int(data["win_x"])
            s.win_y = int(data["win_y"])
    except Exception:
        pass
    return s


def save_settings(s):
    try:
        d = {
            "preview_count": s.preview_count,
            "show_ghost":    s.show_ghost,
            "garbage_rows":  s.garbage_rows,
            "auto_mutate":   s.auto_mutate,
            "teleport":      s.teleport,
            "win_w":         s.win_w,
            "win_h":         s.win_h,
        }
        if s.win_x is not None:
            d["win_x"] = s.win_x
            d["win_y"] = s.win_y
        SETTINGS_FILE.write_text(json.dumps(d))
    except Exception:
        pass


# ── Helpers ────────────────────────────────────────────────

def rotate_cw(matrix):
    return [list(row) for row in zip(*matrix[::-1])]


def filled_cells(matrix):
    return [(r, c) for r, row in enumerate(matrix) for c, v in enumerate(row) if v]


# ── Piece ──────────────────────────────────────────────────

class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.rotations = [SHAPES[kind]]
        m = SHAPES[kind]
        for _ in range(3):
            m = rotate_cw(m)
            self.rotations.append(m)
        self.rot = 0
        self.matrix = self.rotations[0]
        self.col = COLS // 2 - len(self.matrix[0]) // 2
        self.row = 0 if kind != 'I' else -1

    @property
    def cells(self):
        return [(self.row + dr, self.col + dc)
                for dr, dc in filled_cells(self.matrix)]

    def next_rotation(self, direction=1):
        new_rot = (self.rot + direction) % 4
        return self.rotations[new_rot], new_rot


# ── Game logic ─────────────────────────────────────────────

class Game:
    def __init__(self, garbage_rows=0):
        self._reset(garbage_rows)

    def _reset(self, garbage_rows=0):
        self.board = [[None] * COLS for _ in range(ROWS)]
        for r in range(ROWS - garbage_rows, ROWS):
            holes = set(random.sample(range(COLS), random.randint(1, 3)))
            for c in range(COLS):
                if c not in holes:
                    self.board[r][c] = GARBAGE
        self._bag  = []
        self._pieces_in_window    = 0
        self._mutations_in_window = 0
        self._auto_mutate_at      = None
        self._auto_teleport_at    = None
        self._teleport_done       = False
        self.preview = [self._from_bag() for _ in range(MAX_PREVIEW)]
        self.current  = self._spawn()
        self.held     = None
        self.hold_used = False
        self.score = 0
        self.level = 1
        self.lines = 0
        self.game_over = False
        self.paused    = False
        self._gravity_acc = 0
        self._lock_start  = None

    def _from_bag(self):
        if not self._bag:
            self._bag = PIECE_TYPES[:]
            random.shuffle(self._bag)
        return self._bag.pop()

    def _spawn(self):
        kind = self.preview.pop(0)
        self.preview.append(self._from_bag())
        p = Piece(kind)
        if not self._valid(p.row, p.col, p.matrix):
            self.game_over = True
        self._pieces_in_window += 1
        if self._pieces_in_window >= 10:
            self._pieces_in_window    = 0
            self._mutations_in_window = 0
        self._auto_mutate_at   = None
        self._auto_teleport_at = None
        self._teleport_done    = False
        return p

    def _height_ok_for_mutate(self):
        piece_bottom = max((r for r, c in self.current.cells), default=-1)
        for r in range(ROWS):
            if any(self.board[r][c] is not None for c in range(COLS)):
                return r - piece_bottom > 4
        return True  # empty board

    def _can_mutate(self):
        return self._mutations_in_window < 2 and self._height_ok_for_mutate()

    def mutate(self):
        if not self._can_mutate():
            return False
        candidates = [t for t in PIECE_TYPES if t != self.current.kind]
        random.shuffle(candidates)
        for kind in candidates:
            p = Piece(kind)
            p.row = self.current.row
            p.col = self.current.col
            for dc in [0, -1, 1, -2, 2, -3, 3]:
                if self._valid(p.row, p.col + dc, p.matrix):
                    p.col += dc
                    self.current = p
                    self._mutations_in_window += 1
                    self._lock_start = None
                    return True
        return False

    def teleport(self):
        candidates = [c for c in range(COLS)
                      if c != self.current.col and
                      self._valid(self.current.row, c, self.current.matrix)]
        if not candidates:
            return False
        self.current.col = random.choice(candidates)
        self._lock_start = None
        return True

    def _valid(self, row, col, matrix):
        for dr, dc in filled_cells(matrix):
            r, c = row + dr, col + dc
            if c < 0 or c >= COLS or r >= ROWS:
                return False
            if r >= 0 and self.board[r][c] is not None:
                return False
        return True

    def _gravity_ms(self):
        return _GRAVITY[min(self.level - 1, len(_GRAVITY) - 1)]

    def move(self, dc):
        nc = self.current.col + dc
        if self._valid(self.current.row, nc, self.current.matrix):
            self.current.col = nc
            return True
        return False

    def _try_drop(self):
        nr = self.current.row + 1
        if self._valid(nr, self.current.col, self.current.matrix):
            self.current.row = nr
            self._lock_start = None
            return True
        return False

    def soft_drop(self):
        if self._try_drop():
            self.score += 1

    def hard_drop(self):
        dropped = 0
        while self._try_drop():
            dropped += 1
        self.score += dropped * 2
        self._lock()

    def rotate(self, direction=1):
        new_matrix, new_rot = self.current.next_rotation(direction)
        kicks = self._kicks(self.current.rot, new_rot)
        for dc, dr in kicks:
            nr = self.current.row + dr
            nc = self.current.col + dc
            if self._valid(nr, nc, new_matrix):
                self.current.row = nr
                self.current.col = nc
                self.current.rot = new_rot
                self.current.matrix = new_matrix
                return True
        return False

    def _kicks(self, fr, to):
        table = _KICKS_I if self.current.kind == 'I' else _KICKS_JLSTZ
        return [(0, 0)] + table.get((fr, to), [])

    def hold(self):
        if self.hold_used:
            return
        self.hold_used = True
        kind = self.current.kind
        self.current = Piece(self.held) if self.held else self._spawn()
        self.held = kind
        self._lock_start = None

    def _lock(self):
        color = COLORS[self.current.kind]
        for r, c in self.current.cells:
            if 0 <= r < ROWS:
                self.board[r][c] = color
        cleared = self._clear_lines()
        if cleared:
            self.score += SCORE_TABLE.get(cleared, 0) * self.level
            self.lines += cleared
            self.level  = self.lines // 10 + 1
        self.hold_used    = False
        self._lock_start  = None
        self._gravity_acc = 0
        self.current = self._spawn()

    def _clear_lines(self):
        full = [r for r in range(ROWS)
                if all(self.board[r][c] is not None for c in range(COLS))]
        for r in full:
            del self.board[r]
            self.board.insert(0, [None] * COLS)
        return len(full)

    def ghost_row(self):
        row = self.current.row
        while self._valid(row + 1, self.current.col, self.current.matrix):
            row += 1
        return row

    def update(self, dt_ms):
        if self.game_over or self.paused:
            return
        can_drop = self._valid(self.current.row + 1,
                               self.current.col, self.current.matrix)
        if can_drop:
            self._gravity_acc += dt_ms
            threshold = self._gravity_ms()
            while self._gravity_acc >= threshold:
                self._gravity_acc -= threshold
                self._try_drop()
            self._lock_start = None
        else:
            self._gravity_acc = 0
            now = pygame.time.get_ticks()
            if self._lock_start is None:
                self._lock_start = now
            elif now - self._lock_start >= LOCK_DELAY:
                self._lock()


# ── Rendering ──────────────────────────────────────────────

def draw_cell(surf, x, y, color, size, ghost=False):
    rect = pygame.Rect(x + 1, y + 1, size - 2, size - 2)
    if ghost:
        pygame.draw.rect(surf, GHOST, rect)
        pygame.draw.rect(surf, color, rect, max(1, size // 15))
    else:
        pygame.draw.rect(surf, color, rect)
        light = tuple(min(255, v + 60) for v in color)
        dark  = tuple(max(0,   v - 60) for v in color)
        pygame.draw.line(surf, light, rect.topleft,     rect.topright)
        pygame.draw.line(surf, light, rect.topleft,     rect.bottomleft)
        pygame.draw.line(surf, dark,  rect.bottomleft,  rect.bottomright)
        pygame.draw.line(surf, dark,  rect.topright,    rect.bottomright)


def draw_board(surf, game, settings, lo):
    bx, by, bw, bh = lo.board_x, lo.board_y, lo.board_w, lo.board_h
    cell = lo.cell

    pygame.draw.rect(surf, DARK, (bx, by, bw, bh))
    for r in range(ROWS + 1):
        yy = by + r * cell
        pygame.draw.line(surf, GRID_C, (bx, yy), (bx + bw, yy))
    for c in range(COLS + 1):
        xx = bx + c * cell
        pygame.draw.line(surf, GRID_C, (xx, by), (xx, by + bh))
    pygame.draw.rect(surf, BORDER, (bx, by, bw, bh), 2)

    for r in range(ROWS):
        for c in range(COLS):
            color = game.board[r][c]
            if color:
                draw_cell(surf, bx + c * cell, by + r * cell, color, cell)

    if not game.game_over:
        if settings.show_ghost:
            ghost_r = game.ghost_row()
            for dr, dc in filled_cells(game.current.matrix):
                r, c = ghost_r + dr, game.current.col + dc
                if 0 <= r < ROWS:
                    draw_cell(surf, bx + c * cell, by + r * cell,
                              COLORS[game.current.kind], cell, ghost=True)

        for dr, dc in filled_cells(game.current.matrix):
            r, c = game.current.row + dr, game.current.col + dc
            if 0 <= r < ROWS:
                draw_cell(surf, bx + c * cell, by + r * cell,
                          COLORS[game.current.kind], cell)


def draw_mini_piece(surf, kind, cx, cy, cell_size):
    if kind is None:
        return
    matrix = SHAPES[kind]
    rows = len(matrix)
    cols = len(matrix[0])
    ox = cx - cols * cell_size // 2
    oy = cy - rows * cell_size // 2
    for r, row in enumerate(matrix):
        for c, v in enumerate(row):
            if v:
                draw_cell(surf, ox + c * cell_size, oy + r * cell_size,
                          COLORS[kind], cell_size)


def draw_panel(surf, game, settings, lo, fonts):
    font_big, font_med, font_small = fonts
    x, cell = lo.panel_x, lo.cell
    pw = lo.panel_w
    y  = lo.board_y

    mini = max(10, int(cell * 0.73))
    box_w = pw - MARGIN // 2

    def label(text, fy, color=GRAY):
        s = font_small.render(text, True, color)
        surf.blit(s, (x, fy))
        return fy + s.get_height() + 3

    def value(text, fy, fnt=font_med, color=WHITE):
        s = fnt.render(text, True, color)
        surf.blit(s, (x, fy))
        return fy + s.get_height() + 8

    hold_h = mini * 3
    y = label("HOLD", y)
    box = pygame.Rect(x, y, box_w, hold_h)
    pygame.draw.rect(surf, DARK, box)
    pygame.draw.rect(surf, BORDER, box, 1)
    draw_mini_piece(surf, game.held, box.centerx, box.centery, mini)
    y = box.bottom + int(cell * 0.5)

    visible = game.preview[:settings.preview_count]
    if visible:
        y = label("NEXT", y)
        preview_h = mini * 3
        for kind in visible:
            box = pygame.Rect(x, y, box_w, preview_h)
            pygame.draw.rect(surf, DARK, box)
            pygame.draw.rect(surf, BORDER, box, 1)
            draw_mini_piece(surf, kind, box.centerx, box.centery, mini)
            y = box.bottom + int(cell * 0.18)
        y += int(cell * 0.3)
    else:
        y += int(cell * 0.6)

    y = label("SCORE", y)
    y = value(str(game.score), y, font_big)
    y = label("LEVEL", y)
    y = value(str(game.level), y)
    y = label("LINES", y)
    y = value(str(game.lines), y)

    if not game.game_over and settings.auto_mutate:
        remaining = 2 - game._mutations_in_window
        if remaining > 0 and game._height_ok_for_mutate():
            dot_color = ( 80, 210,  80)
        elif remaining > 0:
            dot_color = (180, 140,  40)
        else:
            dot_color = ( 55,  55,  68)
        y = label("MUTATE", y, color=dot_color)
        dots = "\u25cf " * remaining + "\u25cb " * (2 - remaining)
        y = value(dots.strip(), y, font_med, color=dot_color)

    if not game.game_over and settings.teleport:
        tp_color = (80, 210, 80) if not game._teleport_done else (55, 55, 68)
        y = label("TELEPORT", y, color=tp_color)
        dot = "\u25cf" if not game._teleport_done else "\u25cb"
        y = value(dot, y, font_med, color=tp_color)

    hint = font_small.render("Esc: settings", True, (70, 70, 90))
    surf.blit(hint, (x, lo.board_y + lo.board_h - hint.get_height()))

    if game.paused and not game.game_over:
        s = font_med.render("PAUSED", True, WHITE)
        surf.blit(s, (x, y + 8))

    if game.game_over:
        s = font_med.render("GAME OVER", True, (220, 50, 50))
        surf.blit(s, (x, y + 8))
        s2 = font_small.render("R to restart", True, GRAY)
        surf.blit(s2, (x, y + 8 + s.get_height() + 4))


def draw_settings_overlay(surf, settings, sel_idx, lo, fonts):
    _, font_med, font_small = fonts
    box_w = 100 + min(310, lo.win_w - 40)
    box_h = 282
    bx = (lo.win_w - box_w) // 2
    by = (lo.win_h - box_h) // 2

    dim = pygame.Surface((lo.win_w, lo.win_h), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 160))
    surf.blit(dim, (0, 0))

    pygame.draw.rect(surf, OVERLAY, (bx, by, box_w, box_h), border_radius=6)
    pygame.draw.rect(surf, BORDER,  (bx, by, box_w, box_h), 2, border_radius=6)

    title = font_med.render("SETTINGS", True, WHITE)
    surf.blit(title, (bx + (box_w - title.get_width()) // 2, by + 12))
    pygame.draw.line(surf, BORDER, (bx + 10, by + 38), (bx + box_w - 10, by + 38))

    rows = [
        ("Preview pieces", f"< {settings.preview_count} >"),
        ("Landing shadow", "ON" if settings.show_ghost    else "OFF"),
        ("Garbage rows",   f"< {settings.garbage_rows} >"),
        ("Auto-mutate",    "ON" if settings.auto_mutate   else "OFF"),
        ("Teleport",       "ON" if settings.teleport      else "OFF"),
    ]
    row_h = 36
    for i, (lbl, val) in enumerate(rows):
        ry = by + 48 + i * row_h
        if i == sel_idx:
            pygame.draw.rect(surf, HILITE, (bx + 8, ry - 4, box_w - 16, row_h - 2),
                             border_radius=4)
        lbl_s = font_small.render(lbl, True, WHITE)
        val_color = (100, 210, 100) if val == "ON" else \
                    (210, 100, 100) if val == "OFF" else WHITE
        val_s = font_small.render(val, True, val_color)
        surf.blit(lbl_s, (bx + 18, ry + 4))
        surf.blit(val_s,  (bx + box_w - val_s.get_width() - 18, ry + 4))

    if sel_idx == 2:
        note = font_small.render("takes effect on restart (R)", True, (100, 100, 120))
        surf.blit(note, (bx + (box_w - note.get_width()) // 2, by + 48 + len(rows) * row_h - 4))

    hint = font_small.render("↑↓ select   ←→ change   Esc close", True, GRAY)
    surf.blit(hint, (bx + (box_w - hint.get_width()) // 2, by + box_h - 24))


# ── Input handling ─────────────────────────────────────────

class DAS:
    def __init__(self):
        self._held = None
        self._held_since = 0
        self._last_repeat = 0

    def press(self, key, now):
        self._held = key
        self._held_since = now
        self._last_repeat = now

    def release(self, key):
        if self._held == key:
            self._held = None

    def tick(self, now):
        if self._held is None:
            return None
        if (now - self._held_since >= DAS_DELAY and
                now - self._last_repeat >= DAS_REPEAT):
            self._last_repeat = now
            return self._held
        return None


# ── Main ───────────────────────────────────────────────────

def main():
    pygame.init()

    settings = load_settings()

    if settings.win_x is not None:
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{settings.win_x},{settings.win_y}"
    screen = pygame.display.set_mode((settings.win_w, settings.win_h), pygame.RESIZABLE)
    os.environ.pop('SDL_VIDEO_WINDOW_POS', None)

    pygame.display.set_caption("Nulltris")
    clock = pygame.time.Clock()

    lo    = compute_layout(settings.win_w, settings.win_h)
    fonts = make_fonts(lo.cell)

    game          = Game(settings.garbage_rows)
    das           = DAS()
    soft_drop_held = False
    soft_acc      = 0
    settings_open = False
    settings_sel  = 0

    prev_ticks = pygame.time.get_ticks()

    while True:
        now = pygame.time.get_ticks()
        dt  = now - prev_ticks
        prev_ticks = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings(settings)
                pygame.quit()
                sys.exit()

            if event.type == pygame.WINDOWRESIZED:
                settings.win_w = event.x
                settings.win_h = event.y
                lo    = compute_layout(event.x, event.y)
                fonts = make_fonts(lo.cell)

            if event.type == pygame.WINDOWMOVED:
                settings.win_x = event.x
                settings.win_y = event.y

            if event.type == pygame.KEYDOWN:
                k = event.key

                if k == pygame.K_q and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    save_settings(settings)
                    pygame.quit()
                    sys.exit()

                if settings_open:
                    if k in (pygame.K_ESCAPE, pygame.K_RETURN):
                        settings_open = False
                        game.paused   = False
                        save_settings(settings)
                    elif k == pygame.K_UP:
                        settings_sel = (settings_sel - 1) % 5
                    elif k == pygame.K_DOWN:
                        settings_sel = (settings_sel + 1) % 5
                    elif k in (pygame.K_LEFT, pygame.K_RIGHT):
                        delta = 1 if k == pygame.K_RIGHT else -1
                        if settings_sel == 0:
                            settings.preview_count = max(0, min(MAX_PREVIEW,
                                                        settings.preview_count + delta))
                        elif settings_sel == 1:
                            settings.show_ghost = not settings.show_ghost
                        elif settings_sel == 2:
                            settings.garbage_rows = max(0, min(MAX_GARBAGE,
                                                        settings.garbage_rows + delta))
                        elif settings_sel == 3:
                            settings.auto_mutate = not settings.auto_mutate
                        else:
                            settings.teleport = not settings.teleport

                elif k == pygame.K_ESCAPE:
                    settings_open = True
                    game.paused   = True
                    settings_sel  = 0

                elif k == pygame.K_r:
                    game._reset(settings.garbage_rows)
                    das = DAS()
                    soft_drop_held = False
                    soft_acc = 0

                elif k == pygame.K_p:
                    game.paused = not game.paused

                elif not game.game_over and not game.paused:
                    if k in (pygame.K_LEFT, pygame.K_RIGHT):
                        dc = -1 if k == pygame.K_LEFT else 1
                        game.move(dc)
                        das.press(k, now)
                    elif k in (pygame.K_UP, pygame.K_x):
                        game.rotate(-1)          # counter-clockwise
                    elif k in (pygame.K_z, pygame.K_LCTRL, pygame.K_RCTRL):
                        game.rotate(1)           # clockwise
                    elif k == pygame.K_SPACE:
                        game.hard_drop()
                    elif k in (pygame.K_c, pygame.K_LSHIFT, pygame.K_RSHIFT):
                        game.hold()
                    elif k == pygame.K_DOWN:
                        soft_drop_held = True

            if event.type == pygame.KEYUP:
                k = event.key
                das.release(k)
                if k == pygame.K_DOWN:
                    soft_drop_held = False
                    soft_acc = 0

        if not game.game_over and not game.paused:
            repeat_key = das.tick(now)
            if repeat_key is not None:
                game.move(-1 if repeat_key == pygame.K_LEFT else 1)

            if soft_drop_held:
                soft_acc += dt
                threshold = game._gravity_ms() // SOFT_FACTOR
                while soft_acc >= threshold:
                    soft_acc -= threshold
                    game.soft_drop()
            else:
                soft_acc = 0

            game.update(dt)

            if settings.auto_mutate:
                if game._auto_mutate_at is None:
                    game._auto_mutate_at = now + random.randint(400, 1800)
                elif now >= game._auto_mutate_at:
                    game._auto_mutate_at = None
                    game.mutate()

            if settings.teleport and not game._teleport_done:
                if game._auto_teleport_at is None:
                    game._auto_teleport_at = now + random.randint(400, 1800)
                elif now >= game._auto_teleport_at:
                    game._auto_teleport_at = None
                    game._teleport_done = True
                    game.teleport()

        screen.fill(BG)
        draw_board(screen, game, settings, lo)
        draw_panel(screen, game, settings, lo, fonts)
        if settings_open:
            draw_settings_overlay(screen, settings, settings_sel, lo, fonts)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
