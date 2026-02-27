import json
import socket
import time
import serial

PI_BIND_IP = "0.0.0.0"
CMD_PORT   = 9000
LAPTOP_IP  = "192.168.0.1"
TELEM_PORT = 9001

WATCHDOG_TIMEOUT = 1.5
SERIAL_PORT = "/dev/ttyUSB0"
SERIAL_BAUD = 115200

# FIX: increased to 20Hz -- halves response delay without flooding buffer
# Safe because Arduino loop is now 50ms (also 20Hz)
SERIAL_CMD_INTERVAL = 1.0 / 20  # 50ms

def clamp(x, lo=-1.0, hi=1.0):
    try:
        x = float(x)
    except:
        return 0.0
    return max(lo, min(hi, x))

def main():
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind((PI_BIND_IP, CMD_PORT))
    rx.settimeout(0.05)

    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    laptop_addr = (LAPTOP_IP, TELEM_PORT)

    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.05)

    print("[Pi] Waiting for Arduino to initialize...")
    time.sleep(3.0)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    print(f"[Pi] Serial open {SERIAL_PORT} @ {SERIAL_BAUD}")

    last_cmd         = None
    last_cmd_time    = 0.0
    last_telem_time  = 0.0
    last_serial_time = 0.0
    last_arduino     = {}

    print(f"[Pi] CMD listen  udp://0.0.0.0:{CMD_PORT}")
    print(f"[Pi] TELEM send  udp://{LAPTOP_IP}:{TELEM_PORT}")
    print("[Pi] Waiting for commands...")

    while True:
        # 1) Receive latest command from HUD (UDP)
        try:
            data, addr = rx.recvfrom(65535)
            cmd = json.loads(data.decode("utf-8"))
            last_cmd = cmd
            last_cmd_time = time.time()
        except socket.timeout:
            pass
        except Exception:
            pass

        now     = time.time()
        timeout = (now - last_cmd_time) > WATCHDOG_TIMEOUT

        # 2) Compute motor outputs
        arm   = False
        surge = 0.0
        yaw   = 0.0

        if last_cmd and not timeout:
            arm   = bool(last_cmd.get("arm",   False))
            surge = clamp(last_cmd.get("surge", 0.0))
            yaw   = clamp(last_cmd.get("yaw",   0.0))

        if (not arm) or timeout:
            surge = 0.0
            yaw   = 0.0

        left  = clamp(surge + yaw)
        right = clamp(surge - yaw)

        status = "ARMED" if arm and not timeout else "SAFE"
        print(f"[{status}] surge={surge:+.2f} yaw={yaw:+.2f} -> L={left:+.2f} R={right:+.2f}   ", end="\r")

        # 3) Send command to Arduino at 20Hz
        if (now - last_serial_time) >= SERIAL_CMD_INTERVAL:
            L_us    = int(1500 + left  * 400)
            R_us    = int(1500 + right * 400)
            arm_int = 1 if (arm and not timeout) else 0
            try:
                ser.reset_input_buffer()
                ser.write(f"C {L_us} {R_us} {arm_int}\n".encode("utf-8"))
            except Exception as e:
                print(f"\nSERIAL ERROR: {e}")
            last_serial_time = now

        # 4) Read telemetry from Arduino
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("T "):
                line = line[2:]
            if line.startswith("{") and line.endswith("}"):
                last_arduino = json.loads(line)
        except Exception:
            pass

        # 5) Forward telemetry to laptop at ~10Hz
        if (now - last_telem_time) > 0.10:
            telem = {
                "t": now,
                "sens": {
                    "p1":     last_arduino.get("p1_psi",   None),
                    "p2":     last_arduino.get("p2_psi",   None),
                    "laser1": last_arduino.get("dist1_cm", None),
                    "laser2": last_arduino.get("dist2_cm", None),
                },
                "state": {
                    "arm":     arm,
                    "timeout": timeout,
                    "left":    left,
                    "right":   right
                }
            }
            try:
                tx.sendto(json.dumps(telem).encode("utf-8"), laptop_addr)
            except Exception:
                pass
            last_telem_time = now

if __name__ == "__main__":
    main()
