import json
import socket
import time
from dataclasses import dataclass, asdict

@dataclass
class UuvCmd:
    t: float
    mode: str
    arm: bool
    surge: float   # [-1..1]
    yaw: float     # [-1..1]
    heave: float   # [-1..1] (optional; keep 0 for now)
    ballast: float # [-1..1] (optional; keep 0 for now)

def clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, float(x)))

class UdpUuvLink:
    """
    Laptop-side link:
      - send commands to Pi: udp://PI_IP:CMD_PORT
      - optionally receive telemetry: bind to TELEMETRY_PORT
      - optionally send ballast commands: udp://PI_IP:BALLAST_PORT
    """
    def __init__(self, pi_ip="192.168.0.2", cmd_port=9000, telemetry_port=9001, ballast_port=9002):
        self.pi_addr = (pi_ip, cmd_port)
        self.pi_ballast_addr = (pi_ip, ballast_port)

        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tx_ballast = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx.bind(("0.0.0.0", telemetry_port))
        self.rx.setblocking(False)

        self.last_telem = None
        self.last_telem_time = 0.0

    def send(self, cmd: UuvCmd):
        payload = json.dumps(asdict(cmd)).encode("utf-8")
        self.tx.sendto(payload, self.pi_addr)

    def send_ballast(self, command: str):
        self.tx_ballast.sendto(command.encode("utf-8"), self.pi_ballast_addr)

    def poll_telem(self):
        try:
            data, _ = self.rx.recvfrom(65535)
            self.last_telem = json.loads(data.decode("utf-8"))
            self.last_telem_time = time.time()
            return self.last_telem
        except BlockingIOError:
            return None
        except Exception:
            return None
