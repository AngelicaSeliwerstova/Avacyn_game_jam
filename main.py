import pygame


WINDOW_SIZE = (1280, 960)
BACKGROUND_COLOR = (18, 18, 24)
FPS = 60


def main():
    pygame.init()

    try:
        screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("gamek | Step 1")
        clock = pygame.time.Clock()
        running = True

        while running:
            # Сначала обрабатываем действия пользователя и события окна.
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            if not running:
                break

            # Здесь позже появятся обновление игры и отрисовка сцены.
            screen.fill(BACKGROUND_COLOR)
            pygame.display.flip()
            clock.tick(FPS)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
