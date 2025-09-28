import pygame, random, math

# ---------------------- Config ----------------------
W, H      = 720, 760          # a bit taller to fit HUD nicely
PLAY_H    = 720               # playfield height
CELL      = 16
ROWS      = PLAY_H // CELL
COLS      = W // CELL
BALL_R    = 8
SPEED     = 800
FPS       = 60

# Fills are mid-tones; balls are darker accents for contrast.
TEAM_NAMES = ["Sky", "Amber", "Orchid", "Jade"]
TEAM_FILL  = [
    (142, 202, 230),  # Sky
    (255, 183,   3),  # Amber
    (199, 125, 255),  # Orchid
    (129, 199, 132),  # Jade
]
TEAM_BALL  = [
    (  2,  48,  71),  # dark blue for Sky
    (154,  52,  18),  # rust for Amber
    ( 76,  29, 149),  # deep violet for Orchid
    (  6,  95,  70),  # deep teal for Jade
]

BG        = (18, 46, 54)
HUD_TEXT  = (236, 238, 240)
SEPARATOR = (28, 64, 72)
BORDER    = (12, 28, 32)

# ----------------------------------------------------

def clamp(v, lo, hi): return max(lo, min(hi, v))
def rand_dir():
    ang = random.uniform(0, 2*math.pi)
    return math.cos(ang), math.sin(ang)

class Grid:
    # grid[y][x] holds a team id 0..3
    def __init__(self):
        self.data = [[0]*COLS for _ in range(ROWS)]
        self.reset_quadrants()

    def reset_quadrants(self):
        midx = COLS // 2
        midy = ROWS // 2
        for y in range(ROWS):
            for x in range(COLS):
                if x < midx and y < midy:      t = 0
                elif x >= midx and y < midy:   t = 1
                elif x < midx and y >= midy:   t = 2
                else:                           t = 3
                self.data[y][x] = t

    def team_at(self, gx, gy):
        if gx < 0 or gy < 0 or gx >= COLS or gy >= ROWS:
            return None
        return self.data[gy][gx]

    def set_cell(self, gx, gy, team):
        if 0 <= gx < COLS and 0 <= gy < ROWS:
            self.data[gy][gx] = team

    def counts(self):
        cnts = [0, 0, 0, 0]
        for row in self.data:
            for v in row:
                cnts[v] += 1
        return cnts

    def draw(self, screen):
        # Per-cell draw (fast enough for 8px cells at 720p)
        for y in range(ROWS):
            py = y * CELL
            row = self.data[y]
            for x in range(COLS):
                pygame.draw.rect(screen, TEAM_FILL[row[x]], (x*CELL, py, CELL, CELL))

class Ball:
    def __init__(self, x, y, team):
        self.x, self.y = x, y
        dx, dy = rand_dir()
        self.vx, self.vy = dx * SPEED, dy * SPEED
        self.team = team
        self.color = TEAM_BALL[team]

    def reset(self, x, y):
        self.x, self.y = x, y
        dx, dy = rand_dir()
        self.vx, self.vy = dx * SPEED, dy * SPEED

    def step_axis(self, grid: Grid, dt, axis):
        if axis == 'x':
            newx = self.x + self.vx * dt
            if newx < BALL_R or newx > W - BALL_R:
                self.vx *= -1
                return
            rimx = newx + (BALL_R if self.vx > 0 else -BALL_R)
            rimx = clamp(rimx, BALL_R, W - BALL_R)
            cgy = int(self.y // CELL)
            cgx = int(rimx // CELL)
            cell_team = grid.team_at(cgx, cgy)
            if cell_team is not None and cell_team != self.team:
                grid.set_cell(cgx, cgy, self.team)
                self.vx *= -1
                return
            self.x = newx
        else:
            newy = self.y + self.vy * dt
            if newy < BALL_R or newy > PLAY_H - BALL_R:
                self.vy *= -1
                return
            rimy = newy + (BALL_R if self.vy > 0 else -BALL_R)
            rimy = clamp(rimy, BALL_R, PLAY_H - BALL_R)
            cgx = int(self.x // CELL)
            cgy = int(rimy // CELL)
            cell_team = grid.team_at(cgx, cgy)
            if cell_team is not None and cell_team != self.team:
                grid.set_cell(cgx, cgy, self.team)
                self.vy *= -1
                return
            self.y = newy

    def update(self, grid: Grid, dt):
        self.step_axis(grid, dt, 'x')
        self.step_axis(grid, dt, 'y')

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), BALL_R)

def draw_legend(screen, font, counts):
    total = ROWS * COLS
    y = PLAY_H + 10
    margin = 12
    cols = 4
    col_w = (W - 2*margin) // cols

    for t in range(4):
        x = margin + t*col_w
        # swatch
        sw = 18
        pygame.draw.rect(screen, TEAM_FILL[t], (x, y, sw, sw), border_radius=3)
        pygame.draw.rect(screen, BORDER,      (x, y, sw, sw), width=1, border_radius=3)

        # right-align numbers; pad to constant width so glyphs don’t shift
        cnt = counts[t]
        pct = int(100 * cnt / total) if total else 0
        # widths chosen to keep things stable: 6 digits for count, 3 for pct
        text = f" {TEAM_NAMES[t]}  {cnt:6d}  "  #({pct:3d}%)
        tsurf = font.render(text, True, HUD_TEXT)

        # draw text in a fixed rect so later teams don’t push earlier ones
        screen.blit(tsurf, (x + sw + 8, y - 1))

def draw_score_bar(screen, counts):
    total = ROWS * COLS
    if total == 0: return
    bar_w = W - 24
    bar_h = 10
    x = 12
    y = PLAY_H + 36
    # background
    pygame.draw.rect(screen, SEPARATOR, (x-1, y-1, bar_w+2, bar_h+2), border_radius=4)
    # segments
    start = x
    for t in range(4):
        w = int(bar_w * counts[t] / total)
        if t == 3:  # last fills remainder to avoid gaps
            w = x + bar_w - start
        pygame.draw.rect(screen, TEAM_FILL[t], (start, y, w, bar_h), border_radius=4 if t==0 else 0)
        start += w
    # thin border
    pygame.draw.rect(screen, BORDER, (x, y, bar_w, bar_h), width=1, border_radius=4)

def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Quad Paint Pong")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 22)

    grid = Grid()

    balls = [
        Ball(W*0.25, PLAY_H*0.25, team=0),
        Ball(W*0.75, PLAY_H*0.25, team=1),
        Ball(W*0.25, PLAY_H*0.75, team=2),
        Ball(W*0.75, PLAY_H*0.75, team=3),
    ]

    paused = False
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT: running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: running = False
                elif e.key == pygame.K_SPACE: paused = not paused
                elif e.key == pygame.K_r:
                    grid.reset_quadrants()
                    balls[0].reset(W*0.25, PLAY_H*0.25)
                    balls[1].reset(W*0.75, PLAY_H*0.25)
                    balls[2].reset(W*0.25, PLAY_H*0.75)
                    balls[3].reset(W*0.75, PLAY_H*0.75)

        if not paused:
            for b in balls:
                b.update(grid, dt)

        # Draw playfield
        screen.fill(BG)
        grid.draw(screen)
        for b in balls:
            b.draw(screen)

        # HUD area background
        pygame.draw.rect(screen, BG, (0, PLAY_H, W, H - PLAY_H))
        pygame.draw.line(screen, SEPARATOR, (0, PLAY_H), (W, PLAY_H), width=2)

        counts = grid.counts()
        draw_legend(screen, font, counts)
        draw_score_bar(screen, counts)

        # Controls hint
        #hint = font.render("[Space pause | R reset | Esc quit]", True, HUD_TEXT)
        #screen.blit(hint, (12, H - 24))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
