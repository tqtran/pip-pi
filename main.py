#!/usr/bin/env python3
"""
pip-pi: Wrist Control Panel for Raspberry Pi Zero
Screen 1: Touch proof-of-concept — four coloured quadrants, touch feedback.

Display target: 720×400 pixels.
Run with --fullscreen for the Pi; omit the flag for desktop testing.
"""

import sys
import time
import pygame

# ── Display ───────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 720, 400
FPS = 30

# ── Quadrant base colours (top-left, top-right, bottom-left, bottom-right) ───
QUAD_COLORS = [
    (210,  65,  65),   # red
    ( 65, 130, 210),   # blue
    ( 55, 170,  85),   # green
    (210, 175,  45),   # yellow
]
FLASH_WHITE = (255, 255, 255)
EXIT_BUTTON_BG = (35, 35, 35)
EXIT_BUTTON_BORDER = (255, 255, 255)
EXIT_BUTTON_TEXT = (255, 255, 255)

# ── Touch / flash constants ───────────────────────────────────────────────────
TOUCH_RADIUS   = 25    # radius = 25 px → 50 px diameter circle
TOUCH_LIFETIME = 2.0   # seconds the circle stays on screen
FLASH_INTERVAL = 0.10  # seconds per flash half-cycle
FLASH_CYCLES   = 5     # half-cycles (flash on → off → on …)


def quadrant_index(x, y):
    """Return 0-3 for which quadrant the point falls in."""
    col = 1 if x >= WIDTH  // 2 else 0
    row = 1 if y >= HEIGHT // 2 else 0
    return row * 2 + col


def quadrant_rect(idx):
    hw, hh = WIDTH // 2, HEIGHT // 2
    col, row = idx % 2, idx // 2
    return pygame.Rect(col * hw, row * hh, hw, hh)


def exit_button_rect():
    return pygame.Rect(WIDTH - 100, 10, 90, 36)


def finger_pos(event):
    return int(event.x * WIDTH), int(event.y * HEIGHT)


# ── Lightweight state objects ─────────────────────────────────────────────────

class TouchPoint:
    __slots__ = ("x", "y", "born")

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.born = time.monotonic()

    def alive(self):
        return (time.monotonic() - self.born) < TOUCH_LIFETIME


class FlashEffect:
    """Quadrant flash animation triggered by a single touch."""

    def __init__(self, quad_idx):
        self.quad_idx = quad_idx
        self.start    = time.monotonic()
        self._done    = False

    def update(self):
        """Return (active, flash_on).  Call once per frame."""
        if self._done:
            return False, False
        elapsed = time.monotonic() - self.start
        cycle   = int(elapsed / FLASH_INTERVAL)
        if cycle >= FLASH_CYCLES:
            self._done = True
            return False, False
        return True, (cycle % 2 == 0)  # even cycles → white


# ── Rendering ────────────────────────────────────────────────────────────────

def draw_quadrants(screen, flash_quad, flash_on):
    for idx in range(4):
        rect  = quadrant_rect(idx)
        color = FLASH_WHITE if (idx == flash_quad and flash_on) else QUAD_COLORS[idx]
        pygame.draw.rect(screen, color, rect)
    # subtle divider lines
    mid_x, mid_y = WIDTH // 2, HEIGHT // 2
    pygame.draw.line(screen, (0, 0, 0), (mid_x, 0),     (mid_x, HEIGHT), 1)
    pygame.draw.line(screen, (0, 0, 0), (0,     mid_y), (WIDTH,  mid_y), 1)


def draw_touch_circles(screen, touch_points):
    for tp in touch_points:
        pygame.draw.circle(screen, (255, 255, 255), (tp.x, tp.y), TOUCH_RADIUS)
        pygame.draw.circle(screen, (  0,   0,   0), (tp.x, tp.y), TOUCH_RADIUS, 2)


def draw_exit_button(screen, font, rect):
    pygame.draw.rect(screen, EXIT_BUTTON_BG, rect, border_radius=8)
    pygame.draw.rect(screen, EXIT_BUTTON_BORDER, rect, width=2, border_radius=8)
    label = font.render("Exit", True, EXIT_BUTTON_TEXT)
    screen.blit(label, label.get_rect(center=rect.center))


# ── Main loop ────────────────────────────────────────────────────────────────

def main():
    pygame.init()
    pygame.display.set_caption("pip-pi")
    pygame.mouse.set_visible(False)

    flags  = pygame.FULLSCREEN if "--fullscreen" in sys.argv else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    clock  = pygame.time.Clock()
    font   = pygame.font.Font(None, 28)
    exit_rect = exit_button_rect()

    touch_points = []
    flash        = None
    exit_pressed = False

    running = True
    while running:
        # ── Events ──────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if exit_rect.collidepoint(x, y):
                    exit_pressed = True
                    continue
                touch_points.append(TouchPoint(x, y))
                flash = FlashEffect(quadrant_index(x, y))

            elif event.type == pygame.MOUSEBUTTONUP:
                x, y = event.pos
                if exit_pressed and exit_rect.collidepoint(x, y):
                    running = False
                exit_pressed = False

            elif event.type == pygame.FINGERDOWN:
                # FINGERDOWN coordinates are 0.0–1.0 normalised
                x, y = finger_pos(event)
                if exit_rect.collidepoint(x, y):
                    exit_pressed = True
                    continue
                touch_points.append(TouchPoint(x, y))
                flash = FlashEffect(quadrant_index(x, y))

            elif event.type == pygame.FINGERUP:
                x, y = finger_pos(event)
                if exit_pressed and exit_rect.collidepoint(x, y):
                    running = False
                exit_pressed = False

        # ── Update state ────────────────────────────────────────────────────
        touch_points = [tp for tp in touch_points if tp.alive()]

        flash_quad, flash_on = -1, False
        if flash is not None:
            active, flash_on = flash.update()
            if active:
                flash_quad = flash.quad_idx
            else:
                flash = None

        # ── Draw ────────────────────────────────────────────────────────────
        draw_quadrants(screen, flash_quad, flash_on)
        draw_touch_circles(screen, touch_points)
        draw_exit_button(screen, font, exit_rect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
