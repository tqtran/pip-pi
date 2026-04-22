import os
import pygame

os.environ.setdefault("SDL_VIDEODRIVER", "kmsdrm")

pygame.init()
screen = pygame.display.set_mode((480, 320), pygame.FULLSCREEN)
screen.fill((0, 0, 0))
pygame.draw.circle(screen, (255, 0, 0), (240, 160), 80)
pygame.display.flip()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            running = False

pygame.quit()
