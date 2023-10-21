import os
import queue
import signal
import sys
import threading

from evdev import InputDevice, ecodes, list_devices
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

ICONS_FOLDER = os.path.join(os.path.dirname(__file__), "../icons")

KEY_TYPE_CAPS = "caps"
KEY_TYPE_NUMS = "nums"

LEDS = {
    f"{KEY_TYPE_CAPS}": ecodes.LED_CAPSL,
    f"{KEY_TYPE_NUMS}": ecodes.LED_NUML,
}

KEY_CODES = {
    f"{KEY_TYPE_CAPS}": ecodes.KEY_CAPSLOCK,
    f"{KEY_TYPE_NUMS}": ecodes.KEY_NUMLOCK,
}


class LockKeyTrayApp:
    timer: QTimer
    device: InputDevice
    is_quit: bool
    thread: threading.Thread
    queue: queue.Queue
    key_type: str
    tray: QSystemTrayIcon

    def __init__(self, key_type):
        self.key_type = key_type
        self.app = QApplication(sys.argv)
        self.tray = QSystemTrayIcon(self.app)
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.monitor_key)
        self.is_quit = False

        menu = QMenu()
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.app_quit)
        self.tray.setContextMenu(menu)

    def monitor_key(self):
        devices = [InputDevice(path) for path in list_devices()]
        for device in devices:
            if device.capabilities().get(ecodes.EV_LED):
                self.device = device
                self.monitor_lock_key(device)

    def is_key_enabled(self, device):
        return LEDS[self.key_type] in device.leds()

    def monitor_lock_key(self, device):
        print("monitoring device", device.path)
        key_state = self.is_key_enabled(device)
        self.queue.put(key_state)

        while not self.is_quit:
            event = device.read_one()
            if event is None:
                continue
            if event.type == ecodes.EV_LED:
                if event.code == LEDS[self.key_type]:
                    key_state = self.is_key_enabled(device)
                    self.queue.put(key_state)

    def update_tray_icon(self):
        while not self.queue.empty():
            key_state = self.queue.get_nowait()
            icon_path = f"{self.key_type}" + ("_on" if key_state else "_off") + ".png"
            self.tray.setIcon(QIcon(os.path.join(ICONS_FOLDER, icon_path)))

    def run(self):
        self.tray.setIcon(
            QIcon(os.path.join(ICONS_FOLDER, "icons8-num-lock-48_off.png"))
        )
        self.tray.setVisible(True)
        self.tray.show()

        self.thread.start()

        self.timer = QTimer(self.app)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_tray_icon)
        self.timer.start()

        sys.exit(self.app.exec())

    def app_quit(self):
        print("Exiting...")
        self.is_quit = True
        self.thread.join()
        self.timer.stop()
        self.app.quit()


def main(key: str):
    app = LockKeyTrayApp(key)

    signal.signal(signal.SIGINT, lambda *args: app.app_quit())
    signal.signal(signal.SIGTERM, lambda *args: app.app_quit())
    app.run()


def caps():
    main("caps")


def nums():
    main("nums")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ["nums", "caps"]:
        print("Uso: python script_name.py [nums|caps]")
        sys.exit(1)
    main(sys.argv[1])
