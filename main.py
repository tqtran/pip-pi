import pygame

print("before init")
pygame.init()
print("after init")

print("display init?", pygame.display.get_init())

screen = pygame.display.set_mode((720, 480))
print("set_mode worked")

running = True
while running:
    for event in pygame.event.get():
        print(event)
        if event.type == pygame.QUIT:
            running = False

pygame.quit()