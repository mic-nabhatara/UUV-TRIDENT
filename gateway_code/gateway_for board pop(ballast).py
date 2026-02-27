import socket
import time
import serial

PI_BIND_IP  = "0.0.0.0"
BALLAST_PORT = 9002          # UDP port for ballast commands from HUD

SERIAL_PORT = "/dev/ttyUSB1"  # change to actual port when decided
SERIAL_BAUD = 9600

WATCHDOG_TIMEOUT = 1.5  # seconds -- sends "0000" if no command received

def main():
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind((PI_BIND_IP, BALLAST_PORT))
    rx.settimeout(0.05)

    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.05)
    time.sleep(2.0)  # wait for board to initialize
    print(f"[Ballast] Serial open {SERIAL_PORT} @ {SERIAL_BAUD}")
    print(f"[Ballast] Listening on udp://0.0.0.0:{BALLAST_PORT}")

    last_cmd       = "0000"   # safe default -- all valves closed
    last_cmd_time  = 0.0
    last_send_time = 0.0
    SEND_INTERVAL  = 0.10     # send to board at 10Hz

    while True:
        # 1) Receive ballast command from HUD
        try:
            data, addr = rx.recvfrom(1024)
            cmd = data.decode("utf-8").strip()
            # Validate -- must be exactly 4 characters of 0s and 1s
            if len(cmd) == 4 and all(c in "01" for c in cmd):
                last_cmd = cmd
                last_cmd_time = time.time()
        except socket.timeout:
            pass
        except Exception:
            pass

        now     = time.time()
        timeout = (now - last_cmd_time) > WATCHDOG_TIMEOUT

        # 2) Watchdog -- close all valves if no command received
        active_cmd = "0000" if timeout else last_cmd

        status = "TIMEOUT" if timeout else "ACTIVE"
        print(f"[{status}] ballast={active_cmd}   ", end="\r")

        # 3) Send to ballast board at 10Hz
        if (now - last_send_time) >= SEND_INTERVAL:
            try:
                ser.write(f"{active_cmd}\n".encode("utf-8"))
            except Exception as e:
                print(f"\nSERIAL ERROR: {e}")
            last_send_time = now

if __name__ == "__main__":
    main()
