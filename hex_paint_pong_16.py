import pygame, random, math

# ---------------------- Config ----------------------
W, H      = 960, 840          # wider & taller to fit 16-team HUD cleanly
PLAY_W    = 960
PLAY_H    = 720               # playfield height
CELL      = 12
ROWS      = PLAY_H // CELL
COLS      = PLAY_W // CELL
BALL_R    = 8
BASE_SPEED   = 600
SPEED_MIN    = 275
SPEED_MAX    = 1050
SPEED_SMOOTH = 0.25
FPS       = 60

BG        = (18, 46, 54)
HUD_TEXT  = (236, 238, 240)
SEPARATOR = (28, 64, 72)
BORDER    = (12, 28, 32)

# 16 distinct mid-tone fills (no white), with darker “ball” accents
TEAM_NAMES = [
    "Sky","Amber","Orchid","Jade",
    "Coral","Steel","Lime","Fuchsia",
    "Teal","Tangerine","Indigo","Mint",
    "Rose","Gold","Cobalt","Olive"
]
TEAM_FILL = [
    (142,202,230),  # Sky
    (255,183,  3),  # Amber
    (199,125,255),  # Orchid
    (129,199,132),  # Jade
    (255,111, 97),  # Coral
    ( 99,117,137),  # Steel
    (176,201, 38),  # Lime
    (233, 79,156),  # Fuchsia
    (  2,170,176),  # Teal
    (255,138,  0),  # Tangerine
    (121,134,203),  # Indigo
    ( 77,182,172),  # Mint
    (244,143,177),  # Rose
    (212,172, 13),  # Gold
    ( 33,150,243),  # Cobalt
    (124,179, 66),  # Olive
]
TEAM_BALL = [
    (  2, 48, 71),  # Sky ball (deep blue)
    (154, 52, 18),  # Amber ball (rust)
    ( 76, 29,149),  # Orchid ball (deep violet)
    (  6, 95, 70),  # Jade ball (deep teal)
    (153, 32, 24),  # Coral ball
    ( 45, 56, 68),  # Steel ball
    ( 70, 92,  9),  # Lime ball
    (128,  7, 85),  # Fuchsia ball
    (  0, 87, 90),  # Teal ball
    (140, 69,  0),  # Tangerine ball
    ( 43, 53,114),  # Indigo ball
    ( 17, 94, 89),  # Mint ball
    (138, 36, 66),  # Rose ball
    (120, 88,  7),  # Gold ball
    ( 13, 86,167),  # Cobalt ball
    ( 48, 92, 20),  # Olive ball
]

N_TEAMS = 16

# ----------------------------------------------------

def clamp(v, lo, hi): return max(lo, min(hi, v))
def rand_dir():
    ang = random.uniform(0, 2*math.pi)
    return math.cos(ang), math.sin(ang)

def get_mono_font(size):
    candidates = ["DejaVu Sans Mono","Menlo","Consolas","Courier New","Liberation Mono","Monaco"]
    path = pygame.font.match_font(candidates, bold=False, italic=False)
    return pygame.font.Font(path, size) if path else pygame.font.SysFont("courier", size)

# --- Spark particles -------------------------------------------------
def lighten(rgb, factor=1.5):
    r, g, b = rgb
    return (min(255, int(r*factor)),
            min(255, int(g*factor)),
            min(255, int(b*factor)))

class Particle:
    def __init__(self, x, y, color):
        import random, math
        self.x, self.y = x, y
        ang   = random.uniform(0, 2*math.pi)
        speed = random.uniform(80, 220)
        self.vx, self.vy = math.cos(ang)*speed, math.sin(ang)*speed
        self.life = random.uniform(0.18, 0.35)   # seconds remaining
        self.max_life = self.life
        self.size = random.randint(2, 3)
        self.color = color

    def update(self, dt):
        # fade + simple drag
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        drag = 1 - 3*dt
        if drag < 0: drag = 0
        self.vx *= drag
        self.vy *= drag

    def draw(self, screen):
        if self.life <= 0: return
        # alpha proportional to remaining life
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
        screen.blit(s, (int(self.x - self.size), int(self.y - self.size)))

def emit_spark(particles, x, y, team):
    base = TEAM_BALL[team] if 'TEAM_BALL' in globals() else (255, 255, 255)
    col  = lighten(base, 1.5)
    for _ in range(14):     # number of particles per hit
        particles.append(Particle(x, y, col))


class Grid:
    # grid[y][x] holds a team id 0..N_TEAMS-1
    def __init__(self):
        self.data = [[0]*COLS for _ in range(ROWS)]
        self.reset_tiles()

    def reset_tiles(self):
        # Start as a 4x4 mosaic (each quadrant cell assigned one team)
        tiles_x, tiles_y = 4, 4
        tile_w = COLS // tiles_x
        tile_h = ROWS // tiles_y
        t = 0
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for y in range(ty*tile_h, (ty+1)*tile_h if ty < tiles_y-1 else ROWS):
                    row = self.data[y]
                    for x in range(tx*tile_w, (tx+1)*tile_w if tx < tiles_x-1 else COLS):
                        row[x] = t
                t += 1

    def team_at(self, gx, gy):
        if gx < 0 or gy < 0 or gx >= COLS or gy >= ROWS:
            return None
        return self.data[gy][gx]

    def set_cell(self, gx, gy, team):
        if 0 <= gx < COLS and 0 <= gy < ROWS:
            self.data[gy][gx] = team

    def counts(self):
        cnts = [0]*N_TEAMS
        for row in self.data:
            for v in row:
                cnts[v] += 1
        return cnts

    def draw(self, screen):
        for y in range(ROWS):
            py = y * CELL
            row = self.data[y]
            for x in range(COLS):
                pygame.draw.rect(screen, TEAM_FILL[row[x]], (x*CELL, py, CELL, CELL))

def paint_cross(grid, gx, gy, team, axis, dir_sign):
    """
    Paint 4 cells:
      - impact cell (gx, gy)
      - one more 'in front' along travel axis (dir_sign = +1 or -1)
      - two 'side' cells perpendicular to axis
    """
    # center
    grid.set_cell(gx, gy, team)

    # in-front cell
    if axis == 'x':
        gx2, gy2 = gx + dir_sign, gy
        side1, side2 = (gx, gy - 1), (gx, gy + 1)
    else:  # axis == 'y'
        gx2, gy2 = gx, gy + dir_sign
        side1, side2 = (gx - 1, gy), (gx + 1, gy)

    grid.set_cell(gx2, gy2, team)
    grid.set_cell(*side1, team)
    grid.set_cell(*side2, team)                

def update_team_speeds(balls, counts):
    total = ROWS * COLS
    nteams = max(1, len(set(b.team for b in balls)))
    avg = total / nteams
    eps = 1.0
    for b in balls:
        c = counts[b.team]
        target = BASE_SPEED * (avg / (c + eps))
        target = max(SPEED_MIN, min(SPEED_MAX, target))
        b.set_speed_toward(target)  # uses SPEED_SMOOTH

class Ball:
    def __init__(self, x, y, team):
        self.x, self.y = x, y
        dx, dy = rand_dir()
        self.vx, self.vy = dx * BASE_SPEED, dy * BASE_SPEED  # was SPEED
        self.team = team
        self.color = TEAM_BALL[team]

    def reset(self, x, y):
        self.x, self.y = x, y
        dx, dy = rand_dir()
        self.vx, self.vy = dx * BASE_SPEED, dy * BASE_SPEED  # was SPEED

    def set_speed_toward(self, target_speed, smooth=SPEED_SMOOTH):
        """Scale (vx,vy) so |v| moves toward target_speed with simple exponential smoothing."""
        vx, vy = self.vx, self.vy
        cur = math.hypot(vx, vy)
        if cur <= 1e-6:
            # dead stop? give it a nudge in a random direction
            ang = random.uniform(0, 2*math.pi)
            self.vx = math.cos(ang) * target_speed
            self.vy = math.sin(ang) * target_speed
            return
        # blend current magnitude toward target
        new_mag = (1.0 - smooth) * cur + smooth * target_speed
        scale = new_mag / cur
        self.vx *= scale
        self.vy *= scale

    def step_axis(self, grid, dt, axis, particles):
        if axis == 'x':
            newx = self.x + self.vx * dt
            if newx < BALL_R or newx > PLAY_W - BALL_R:
                self.vx *= -1
                return
            dir_sign = 1 if self.vx > 0 else -1
            rimx = newx + (BALL_R if dir_sign > 0 else -BALL_R)
            rimx = clamp(rimx, BALL_R, PLAY_W - BALL_R)
            cgy = int(self.y // CELL)
            cgx = int(rimx // CELL)
            cell_team = grid.team_at(cgx, cgy)

            if cell_team is not None and cell_team != self.team:
                paint_cross(grid, cgx, cgy, self.team, axis='x', dir_sign=dir_sign)
                # emit spark at center of impact cell
                hit_x = cgx * CELL + CELL/2
                hit_y = cgy * CELL + CELL/2
                emit_spark(particles, hit_x, hit_y, self.team)
                self.vx *= -1
                return
            self.x = newx

        else:  # axis == 'y'
            newy = self.y + self.vy * dt
            if newy < BALL_R or newy > PLAY_H - BALL_R:
                self.vy *= -1
                return
            dir_sign = 1 if self.vy > 0 else -1
            rimy = newy + (BALL_R if dir_sign > 0 else -BALL_R)
            rimy = clamp(rimy, BALL_R, PLAY_H - BALL_R)
            cgx = int(self.x // CELL)
            cgy = int(rimy // CELL)
            cell_team = grid.team_at(cgx, cgy)

            if cell_team is not None and cell_team != self.team:
                paint_cross(grid, cgx, cgy, self.team, axis='y', dir_sign=dir_sign)
                hit_x = cgx * CELL + CELL/2
                hit_y = cgy * CELL + CELL/2
                emit_spark(particles, hit_x, hit_y, self.team)
                self.vy *= -1
                return
            self.y = newy

    def update(self, grid, dt, particles):
        self.step_axis(grid, dt, 'x', particles)
        self.step_axis(grid, dt, 'y', particles)

    def draw(self, screen):
        # ball with subtle dark outline for visibility
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), BALL_R)
        pygame.draw.circle(screen, BORDER, (int(self.x), int(self.y)), BALL_R, 1)

def layout_start_positions(n, cols=4, rows=4):
    # Place n balls on a cols×rows grid of anchor points inside the playfield
    xs = [(i+0.5)*(PLAY_W/cols) for i in range(cols)]
    ys = [(j+0.5)*(PLAY_H/rows) for j in range(rows)]
    pts = []
    for j in range(rows):
        for i in range(cols):
            pts.append((xs[i], ys[j]))
    return pts[:n]

def draw_legend(screen, font, counts):
    total = ROWS * COLS  # not used now, but fine to keep
    margin_x = 12
    top_y    = PLAY_H + 10
    cols     = 4
    rows     = 4
    col_w    = (W - 2*margin_x) // cols
    row_h    = 26  # was 24; a bit more breathing room

    for idx in range(N_TEAMS):
        r = idx // cols
        c = idx % cols
        x = margin_x + c * col_w
        y = top_y + r * row_h

        # color swatch
        sw = 14
        pygame.draw.rect(screen, TEAM_FILL[idx], (x, y, sw, sw), border_radius=3)
        pygame.draw.rect(screen, BORDER,        (x, y, sw, sw), width=1, border_radius=3)

        # counts ONLY (monospace font prevents jitter)
        cnt   = counts[idx]
        label = f" {TEAM_NAMES[idx]:<8} {cnt:6d}"
        tsurf = font.render(label, True, HUD_TEXT)

        # keep everything in this column cell; no overlap with neighbors
        screen.blit(tsurf, (x + sw + 6, y - 2))

def draw_score_bar(screen, counts):
    bar_w = W - 24
    bar_h = 12
    x = 12
    # legend occupies 4*row_h + ~10px → 4*26 + 10 = 114; start bar below that
    y = PLAY_H + 10 + 4*26 + 8
    pygame.draw.rect(screen, SEPARATOR, (x-1, y-1, bar_w+2, bar_h+2), border_radius=4)
    start = x
    total = ROWS * COLS
    for t in range(N_TEAMS):
        w = int(bar_w * counts[t] / total) if t < N_TEAMS - 1 else (x + bar_w - start)
        pygame.draw.rect(screen, TEAM_FILL[t], (start, y, w, bar_h), border_radius=4 if t==0 else 0)
        start += w
    pygame.draw.rect(screen, BORDER, (x, y, bar_w, bar_h), width=1, border_radius=4)

def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Hex Paint Pong — 16 teams")
    clock = pygame.time.Clock()
    font = get_mono_font(18)
    particles = []

    grid = Grid()

    anchors = layout_start_positions(N_TEAMS, cols=4, rows=4)
    balls = [Ball(ax, ay, team=i) for i, (ax, ay) in enumerate(anchors)]

    paused = False
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0

        counts = grid.counts()
        # adjust team speeds toward equilibrium
        update_team_speeds(balls, counts)

        for e in pygame.event.get():
            if e.type == pygame.QUIT: running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: running = False
                elif e.key == pygame.K_SPACE: paused = not paused
                elif e.key == pygame.K_r:
                    grid.reset_tiles()
                    anchors = layout_start_positions(N_TEAMS, cols=4, rows=4)
                    for i, b in enumerate(balls):
                        ax, ay = anchors[i]
                        b.reset(ax, ay)

        if not paused:
            for b in balls:
                b.update(grid, dt, particles)
            # particles update & prune
            for p in particles[:]:
                p.update(dt)
                if p.life <= 0:
                    particles.remove(p)

        # DRAW
        screen.fill(BG)
        grid.draw(screen)

        # draw particles (above board)
        for p in particles:
            p.draw(screen)

        # draw balls on top
        for b in balls:
            b.draw(screen)

        # HUD area
        pygame.draw.rect(screen, BG, (0, PLAY_H, W, H - PLAY_H))
        pygame.draw.line(screen, SEPARATOR, (0, PLAY_H), (W, PLAY_H), width=2)

        counts = grid.counts()
        draw_legend(screen, font, counts)
        draw_score_bar(screen, counts)

        # Help
        #hint = font.render("[Space pause | R reset | Esc quit]", True, HUD_TEXT)
        #screen.blit(hint, (12, H - 28))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
