import os
import queue
import signal
import sys
import threading
import argparse
import time
from typing import Optional

from evdev import InputDevice, ecodes, list_devices, UInput
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
    initial_state: Optional[bool]

    def __init__(self, key_type, initial_state: Optional[bool] = None):
        self.key_type = key_type
        self.initial_state = initial_state
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
                self.set_key_state()
                self.monitor_lock_key(device)

    def is_key_enabled(self, device):
        return LEDS[self.key_type] in device.leds()

    def set_key_state(self):
        if self.device is None:
            return

        if self.initial_state is None:
            return

        if self.initial_state != self.is_key_enabled(self.device):
            ui = UInput()
            ui.write(ecodes.EV_KEY, KEY_CODES[self.key_type], 1)
            ui.syn()
            ui.write(ecodes.EV_KEY, KEY_CODES[self.key_type], 0)
            ui.syn()

    def monitor_lock_key(self, device):
        key_state = self.is_key_enabled(device)
        self.queue.put(key_state)

        while not self.is_quit:
            event = device.read_one()
            if event is None:
                time.sleep(0.05)
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


def main(key: str, set_on: Optional[bool] = None):
    app = LockKeyTrayApp(key, set_on)

    signal.signal(signal.SIGINT, lambda *args: app.app_quit())
    signal.signal(signal.SIGTERM, lambda *args: app.app_quit())
    app.run()


def caps():
    cap_args = get_args("caps")
    main(cap_args.key, cap_args.set_on)


def nums():
    num_args = get_args("nums")
    main(num_args.key, num_args.set_on)


def get_args(default=None):
    arg_parser = argparse.ArgumentParser()
    # make it optional if default is pass it
    key_param_name = "key" if default is None else '--key'
    arg_parser.add_argument(key_param_name, choices=["caps", "nums"], default=default, help="Key to monitor")
    arg_parser.add_argument("--set-on", default=None, action="store_true", help="Set initial state to ON")
    return arg_parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    main(args.key, args.set_on)
