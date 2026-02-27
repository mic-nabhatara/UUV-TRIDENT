import pygame
import cv2
import math
import numpy as np
import time

from uuv_link import UdpUuvLink, UuvCmd, clamp

# Network / video settings
PI_IP = "192.168.0.2"
PI_PORT = 8000

GST_PIPE = (
    f"tcpclientsrc host={PI_IP} port={PI_PORT} ! "
    "h264parse ! avdec_h264 ! videoconvert ! "
    "video/x-raw,format=BGR ! appsink drop=true max-buffers=2 sync=false"
)

# Window size
win_w, win_h = 1000, 750

# demo values (later replace with telemetry)
d1 = 1.0
d2 = 1.1


def make_green(icon: pygame.Surface) -> pygame.Surface:
    """Make a green-tinted version of an icon (keeps alpha)."""
    g = icon.copy()
    g.fill((0, 255, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    # small brighten boost so it pops
    g.fill((0, 80, 0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return g

def draw_guidelines(screen, dist_m, win_w, win_h):
    """
    Draw 2 slanted parking-style guide lines
    Color-coded by distance (green/yellow/red)
    """

    # Center horizontally between WASD and arrows
    center_x = win_w // 2
    base_y = win_h - 120          # start near key icons
    top_y = win_h // 2            # end in upper half

    # How wide the funnel is
    bottom_width = 400
    top_width = 100

    # Distance thresholds (meters)
    green_d = 1.5
    yellow_d = 0.8

    # Split vertical space into 3 sections
    total_h = base_y - top_y
    section_h = total_h // 3

    sections = [
        # (y_start, y_end, color, visible)
        (base_y, base_y - section_h, (0, 255, 0), dist_m <= yellow_d),       # green
        (base_y - section_h, base_y - 2*section_h, (255, 255, 0), dist_m <= green_d), # YELLOW
        (base_y - 2*section_h, top_y, (255, 0, 0), True),                     # red
    ]

    for y1, y2, color, visible in sections:
        if not visible:
            continue

        # Interpolate width at y
        def width_at(y):
            t = (base_y - y) / total_h
            return bottom_width + t * (top_width - bottom_width)

        w1 = width_at(y1)
        w2 = width_at(y2)

        # Left line
        pygame.draw.line(
            screen, color,
            (center_x - w1//2, y1),
            (center_x - w2//2, y2),
            4
        )

        # Right line
        pygame.draw.line(
            screen, color,
            (center_x + w1//2, y1),
            (center_x + w2//2, y2),
            4
        )

def main():
    pygame.init()
    font = pygame.font.SysFont("Arial", 22)

    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption("UUV HUD")

    # Load UI icons
    pic_kw = pygame.image.load("src/keyw.png").convert_alpha()
    pic_ka = pygame.image.load("src/keya.png").convert_alpha()
    pic_ks = pygame.image.load("src/keys.png").convert_alpha()
    pic_kd = pygame.image.load("src/keyd.png").convert_alpha()

    pic_battery = pygame.image.load("src/battery.png").convert_alpha()
    pic_depth = pygame.image.load("src/depth.png").convert_alpha()
    pic_laser = pygame.image.load("src/laser.png").convert_alpha()

    pic_up = pygame.image.load("src/arrow.png").convert_alpha()
    pic_left = pygame.transform.rotate(pic_up, 90)
    pic_down = pygame.transform.rotate(pic_up, 180)
    pic_right = pygame.transform.rotate(pic_up, 270)

    pic_pitch = pygame.image.load("src/pitch.png").convert_alpha()
    pic_pitchl = pygame.image.load("src/pitchl.png").convert_alpha()

    # Green versions
    pic_kw_g = make_green(pic_kw)
    pic_ka_g = make_green(pic_ka)
    pic_ks_g = make_green(pic_ks)
    pic_kd_g = make_green(pic_kd)

    pic_up_g = make_green(pic_up)
    pic_left_g = make_green(pic_left)
    pic_down_g = make_green(pic_down)
    pic_right_g = make_green(pic_right)

    # Video capture from Pi
    cap = cv2.VideoCapture(GST_PIPE, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("ERROR: cannot open stream; check GStreamer and Pi connection")
        return

    # UDP link to Pi gateway
    link = UdpUuvLink(pi_ip=PI_IP, cmd_port=9000, telemetry_port=9001)
    armed = False

    clock = pygame.time.Clock()
    running = True
    L = True

    # last telemetry cache for display
    last_telem = None

    while running:
        # -----------------------------
        # 1) Events
        # -----------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_RETURN:  # Enter toggles ARM
                    armed = not armed
                    print("ARM =", armed)

    
        keys = pygame.key.get_pressed()
        kw = keys[pygame.K_w]
        ka = keys[pygame.K_a]
        ks = keys[pygame.K_s]
        kd = keys[pygame.K_d]

        up = keys[pygame.K_UP]
        left = keys[pygame.K_LEFT]
        down = keys[pygame.K_DOWN]
        right = keys[pygame.K_RIGHT]

        
        # Convert keys -> surge/yaw and send to Pi

        surge = (1.0 if kw else 0.0) + (-1.0 if ks else 0.0)
        yaw = (1.0 if ka else 0.0) + (-1.0 if kd else 0.0)

        surge = clamp(surge)
        yaw = clamp(yaw)

        cmd = UuvCmd(
            t=time.time(),
            mode="MANUAL",
            arm=armed,
            surge=surge,
            yaw=yaw,
            heave=0.0,
            ballast=0.0
        )
        link.send(cmd)

        # receive telemetry if any
        telem = link.poll_telem()
        if telem is not None:
            last_telem = telem

        # Read camera frame
        ret, frame = cap.read()
        if not ret:
            pygame.time.wait(10)
            continue

        frame = cv2.resize(frame, (win_w, win_h))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.surfarray.make_surface(np.rot90(frame))

  
        # Draw
        screen.fill((0, 0, 0))
        screen.blit(frame_surface, (0, 0))

        # Static icons
        screen.blit(pic_depth, (10, 10))
        screen.blit(pic_laser, (10, 70))
        screen.blit(pic_battery, (10, 130))

        # Keys (green when pressed)
        screen.blit(pic_kw_g if kw else pic_kw, (120, 570))
        screen.blit(pic_ka_g if ka else pic_ka, (40, 650))
        screen.blit(pic_ks_g if ks else pic_ks, (120, 650))
        screen.blit(pic_kd_g if kd else pic_kd, (200, 650))

        screen.blit(pic_up_g if up else pic_up, (800, 570))
        screen.blit(pic_left_g if left else pic_left, (720, 650))
        screen.blit(pic_down_g if down else pic_down, (800, 650))
        screen.blit(pic_right_g if right else pic_right, (880, 650))

        # Demo text (replace later)
        screen.blit(font.render(f"{d1:.2f}m", True, (200, 200, 200)), (70, 30))
        screen.blit(font.render(f"{d2:.2f}m", True, (200, 200, 200)), (120, 30))
        screen.blit(font.render("50%", True, (200, 200, 200)), (70, 150))

        # Command display
        screen.blit(font.render(f"ARM: {armed} (Enter toggle)", True, (200, 200, 200)), (10, 200))
        screen.blit(font.render(f"CMD surge={surge:+.1f} yaw={yaw:+.1f}", True, (200, 200, 200)), (10, 230))

        #Guideline
        dist_m = 0.9  # example
        draw_guidelines(screen, dist_m, win_w, win_h)

        # Telemetry display (from gateway.py)
        if last_telem:
            p1 = last_telem.get("sens", {}).get("p1", None)
            p2 = last_telem.get("sens", {}).get("p2", None)
            laser = last_telem.get("sens", {}).get("laser", None)

            timeout = last_telem.get("state", {}).get("timeout", None)
            Lout = last_telem.get("state", {}).get("left", None)
            Rout = last_telem.get("state", {}).get("right", None)

            screen.blit(font.render(f"TELEM p1={p1} p2={p2} laser={laser}", True, (200, 200, 200)), (10, 260))
            screen.blit(font.render(f"STATE timeout={timeout} L={Lout} R={Rout}", True, (200, 200, 200)), (10, 290))

        # Pitch (demo)
        pitch_angle = int(math.degrees(math.atan((d1 - d2) / 0.22)))
        pitch = pygame.transform.rotate(pic_pitchl if L else pic_pitch, pitch_angle)
        pitchFrame = pitch.get_rect(center=(900, 75))
        screen.blit(pitch, pitchFrame.topleft)
        
        pygame.display.flip()
        clock.tick(30)

    cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()
