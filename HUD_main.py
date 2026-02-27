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

def make_green(icon: pygame.Surface) -> pygame.Surface:
    g = icon.copy()
    g.fill((0, 255, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    g.fill((0, 80, 0, 0),    special_flags=pygame.BLEND_RGBA_ADD)
    return g


def main():
    pygame.init()
    font      = pygame.font.SysFont("Arial", 22)
    font_small = pygame.font.SysFont("Arial", 18)

    win_w, win_h = 1000, 750
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption("UUV HUD")

    # Load UI icons
    pic_kw = pygame.image.load("src/keyw.png").convert_alpha()
    pic_ka = pygame.image.load("src/keya.png").convert_alpha()
    pic_ks = pygame.image.load("src/keys.png").convert_alpha()
    pic_kd = pygame.image.load("src/keyd.png").convert_alpha()

    pic_battery = pygame.image.load("src/battery.png").convert_alpha()
    pic_depth   = pygame.image.load("src/depth.png").convert_alpha()
    pic_laser   = pygame.image.load("src/laser.png").convert_alpha()

    pic_up    = pygame.image.load("src/arrow.png").convert_alpha()
    pic_left  = pygame.transform.rotate(pic_up, 90)
    pic_down  = pygame.transform.rotate(pic_up, 180)
    pic_right = pygame.transform.rotate(pic_up, 270)

    pic_pitch  = pygame.image.load("src/pitch.png").convert_alpha()
    pic_pitchl = pygame.image.load("src/pitchl.png").convert_alpha()

    # Green versions
    pic_kw_g    = make_green(pic_kw)
    pic_ka_g    = make_green(pic_ka)
    pic_ks_g    = make_green(pic_ks)
    pic_kd_g    = make_green(pic_kd)
    pic_up_g    = make_green(pic_up)
    pic_left_g  = make_green(pic_left)
    pic_down_g  = make_green(pic_down)
    pic_right_g = make_green(pic_right)

    # Video capture from Pi
    cap = cv2.VideoCapture(GST_PIPE, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("ERROR: cannot open stream; check GStreamer and Pi connection")
        return

    # UDP link to Pi gateway
    link   = UdpUuvLink(pi_ip=PI_IP, cmd_port=9000, telemetry_port=9001, ballast_port=9002)
    armed  = False

    clock     = pygame.time.Clock()
    running   = True
    last_telem = None

    while running:
        # 1) Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_RETURN:
                    armed = not armed
                    print("ARM =", armed)

        # 2) Keys
        keys = pygame.key.get_pressed()
        kw = keys[pygame.K_w]
        ka = keys[pygame.K_a]
        ks = keys[pygame.K_s]
        kd = keys[pygame.K_d]

        ki = keys[pygame.K_i]
        kk = keys[pygame.K_k]
        ko = keys[pygame.K_o]
        kl = keys[pygame.K_l]

        up    = keys[pygame.K_UP]
        left  = keys[pygame.K_LEFT]
        down  = keys[pygame.K_DOWN]
        right = keys[pygame.K_RIGHT]
        
        # BALLAST
        command_ballast = f"{1 if kk else 0}{1 if ki or kk else 0}{1 if kl else 0}{1 if ko or kl else 0}"

        # 3) Build and send command
        surge = clamp((1.0 if kw else 0.0) + (-1.0 if ks else 0.0))
        yaw   = clamp((1.0 if ka else 0.0) + (-1.0 if kd else 0.0))

        cmd = UuvCmd(
            t=time.time(), mode="MANUAL", arm=armed,
            surge=surge, yaw=yaw, heave=0.0, ballast=0.0
        )
        link.send(cmd)

        # 4) Receive telemetry
        telem = link.poll_telem()
        if telem is not None:
            last_telem = telem
        # Send ballast command
        link.send_ballast(command_ballast)

        # 5) Read camera frame
        ret, frame = cap.read()
        if not ret:
            pygame.time.wait(10)
            continue

        frame = cv2.resize(frame, (win_w, win_h))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.surfarray.make_surface(np.rot90(frame))

        # 6) Draw
        screen.fill((0, 0, 0))
        screen.blit(frame_surface, (0, 0))

        # Static icons
        screen.blit(pic_depth,   (10, 10))
        screen.blit(pic_laser,   (10, 70))
        screen.blit(pic_battery, (10, 130))

        # WASD keys
        screen.blit(pic_kw_g if kw else pic_kw, (120, 570))
        screen.blit(pic_ka_g if ka else pic_ka, (40,  650))
        screen.blit(pic_ks_g if ks else pic_ks, (120, 650))
        screen.blit(pic_kd_g if kd else pic_kd, (200, 650))

        # Arrow keys
        screen.blit(pic_up_g    if up    else pic_up,    (800, 570))
        screen.blit(pic_left_g  if left  else pic_left,  (720, 650))
        screen.blit(pic_down_g  if down  else pic_down,  (800, 650))
        screen.blit(pic_right_g if right else pic_right, (880, 650))

        # Command display
        screen.blit(font.render(f"ARM: {armed} (Enter to toggle)", True, (200, 200, 200)), (10, 200))
        screen.blit(font.render(f"CMD surge={surge:+.1f} yaw={yaw:+.1f}", True, (200, 200, 200)), (10, 230))

        # Telemetry display -- all values from real Arduino sensors
        # FIX: reads p1, p2, laser1, laser2 to match updated gateway/Arduino
        p1     = None
        p2     = None
        laser1 = None
        laser2 = None

        if last_telem:
            sens   = last_telem.get("sens", {})
            state  = last_telem.get("state", {})

            p1     = sens.get("p1",     None)
            p2     = sens.get("p2",     None)
            laser1 = sens.get("laser1", None)
            laser2 = sens.get("laser2", None)

            timeout = state.get("timeout", None)
            Lout    = state.get("left",    None)
            Rout    = state.get("right",   None)

            # Sensor readouts next to icons
            p1_str     = f"{p1:.1f} PSI"     if p1     is not None else "N/A"
            p2_str     = f"{p2:.1f} PSI"     if p2     is not None else "N/A"
            l1_str     = f"{laser1:.1f} cm"  if laser1 is not None else "N/A"
            l2_str     = f"{laser2:.1f} cm"  if laser2 is not None else "N/A"

            screen.blit(font.render(f"P1: {p1_str}  P2: {p2_str}",    True, (200, 200, 200)), (70, 15))
            screen.blit(font.render(f"L1: {l1_str}  L2: {l2_str}",    True, (200, 200, 200)), (70, 75))
            screen.blit(font.render(f"STATE timeout={timeout} L={Lout:.2f} R={Rout:.2f}" if Lout is not None
                                     else f"STATE timeout={timeout}", True, (200, 200, 200)), (10, 260))

        # Pitch -- FIX: use real laser1/laser2 from telemetry instead of hardcoded d1/d2
        # Falls back to 0 degrees if sensors not available
        if laser1 is not None and laser2 is not None:
            d1 = laser1 / 100.0  # cm to metres
            d2 = laser2 / 100.0
            pitch_angle = int(math.degrees(math.atan((d1 - d2) / 0.22)))
            use_left    = d1 > d2
        else:
            pitch_angle = 0
            use_left    = False

        pitch      = pygame.transform.rotate(pic_pitchl if use_left else pic_pitch, pitch_angle)
        pitchFrame = pitch.get_rect(center=(900, 75))
        screen.blit(pitch, pitchFrame.topleft)

        pygame.display.flip()
        clock.tick(30)

    cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()