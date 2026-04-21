import os
import pygame

print("SDL_VIDEODRIVER =", os.environ.get("SDL_VIDEODRIVER"))
print("before init")
pygame.init()
print("after init")
print("display init?", pygame.display.get_init())
print("about to set_mode")
screen = pygame.display.set_mode((480, 320))
print("driver =", pygame.display.get_driver())
print("set_mode worked")