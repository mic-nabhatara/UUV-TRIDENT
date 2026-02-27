import pygame
import numpy as np

pygame.init()
screen = pygame.display.set_mode((600, 400))
pygame.display.set_caption("Ballast Test")
font = pygame.font.SysFont("Arial", 22)
clock = pygame.time.Clock()

running = True
while running:
    # Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                running = False

    # Keys
    keys = pygame.key.get_pressed()
    ki = keys[pygame.K_i]
    kk = keys[pygame.K_k]
    ko = keys[pygame.K_o]
    kl = keys[pygame.K_l]

    # Ballast command string
    command_ballast = f"{1 if kk else 0}{1 if ki or kk else 0}{1 if kl else 0}{1 if ko or kl else 0}"

    # Draw
    screen.fill((20, 20, 20))

    # Show ballast command
    screen.blit(font.render(f"BALLAST: {command_ballast}", True, (0, 255, 0)), (20, 20))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()