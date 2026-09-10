"""ESP32 hardware integration."""
import threading
import time
from typing import Optional
from app.core.config import settings


class ESP32Controller:
    """
    Optional ESP32 serial integration.
    Falls back to software simulation if not connected.
    """
    CMD_GREEN = b'G'
    CMD_RED = b'R'
    CMD_BUZZER = b'B'
    CMD_OFF = b'0'

    def __init__(self):
        self._serial = None
        self._connected = False
        self._simulated = not settings.ESP32_ENABLED
        self._lock = threading.Lock()

    def connect(self, port: Optional[str] = None, baud: int = 115200) -> bool:
        if self._simulated:
            print("[ESP32] Simulation mode: no hardware connected")
            return True
        try:
            import serial
            p = port or settings.ESP32_PORT
            self._serial = serial.Serial(p, baud, timeout=1)
            self._connected = True
            print(f"[ESP32] Connected on {p} @ {baud}")
            return True
        except Exception as e:
            print(f"[ESP32] Connection failed: {e}. Falling back to simulation.")
            self._simulated = True
            return False

    def disconnect(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._connected = False

    def send(self, cmd: bytes):
        with self._lock:
            if self._simulated:
                labels = {b'G': '🟢 GREEN', b'R': '🔴 RED', b'B': '🔔 BUZZER', b'0': '⬛ OFF'}
                print(f"[ESP32 SIM] {labels.get(cmd, cmd)}")
                return
            if self._serial and self._serial.is_open:
                try:
                    self._serial.write(cmd)
                except Exception as e:
                    print(f"[ESP32] Write error: {e}")

    def signal_correct(self):
        """Green LED: correct step."""
        self.send(self.CMD_GREEN)
        threading.Timer(1.5, lambda: self.send(self.CMD_OFF)).start()

    def signal_error(self):
        """Red LED: error detected."""
        self.send(self.CMD_RED)
        threading.Timer(2.0, lambda: self.send(self.CMD_OFF)).start()

    def signal_complete(self):
        """Green blink: procedure complete."""
        def blink():
            for _ in range(3):
                self.send(self.CMD_GREEN)
                time.sleep(0.3)
                self.send(self.CMD_OFF)
                time.sleep(0.2)
        threading.Thread(target=blink, daemon=True).start()

    def signal_critical_error(self):
        """Buzzer + red: critical training error."""
        self.send(self.CMD_BUZZER)
        self.send(self.CMD_RED)
        threading.Timer(2.0, lambda: self.send(self.CMD_OFF)).start()

    @property
    def is_connected(self) -> bool:
        return self._connected or self._simulated

    @property
    def is_simulated(self) -> bool:
        return self._simulated


_esp32: Optional[ESP32Controller] = None


def get_esp32() -> ESP32Controller:
    global _esp32
    if _esp32 is None:
        _esp32 = ESP32Controller()
        _esp32.connect()
    return _esp32
