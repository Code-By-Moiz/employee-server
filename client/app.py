import sys
import os
import json
import time
from datetime import datetime

import requests
import pyautogui

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QSystemTrayIcon, QMenu, QMessageBox, QDialog, QFrame
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QTimer, Qt

try:
    import win32gui
    HAS_WIN32GUI = True
except ImportError:
    HAS_WIN32GUI = False

SERVER_URL = "http://localhost:8000/api/upload"
CONFIG_FILE = "config.json"
CACHE_DIR = "offline_cache"
SCREENSHOT_INTERVAL_MS = 30000

os.makedirs(CACHE_DIR, exist_ok=True)


def get_active_window_title():
    if not HAS_WIN32GUI:
        return "Unknown"
    try:
        window = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(window)
    except Exception:
        return "Unknown"


class SummaryDialog(QDialog):
    def __init__(self, work_seconds, break_seconds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Daily Work Summary")
        self.setFixedSize(320, 240)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #f8fafc; }
            QLabel { color: #f8fafc; font-size: 13px; }
            QPushButton { background-color: #3b82f6; color: white; border-radius: 6px; padding: 8px; font-weight: bold; }
        """)

        layout = QVBoxLayout()

        title = QLabel("📊 Shift Summary")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8; margin-bottom: 8px;")
        layout.addWidget(title)

        work_h = work_seconds // 3600
        work_m = (work_seconds % 3600) // 60
        break_h = break_seconds // 3600
        break_m = (break_seconds % 3600) // 60

        lbl_work = QLabel(f"⏱️ Total Active Work: {work_h}h {work_m}m")
        lbl_break = QLabel(f"☕ Total Break Time: {break_h}h {break_m}m")
        
        layout.addWidget(lbl_work)
        layout.addWidget(lbl_break)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.setLayout(layout)


class EmployeeApp(QWidget):
    def __init__(self):
        super().__init__()
        self.employee_name = ""
        self.is_tracking = False
        self.on_break = False

        self.work_seconds = 0
        self.break_seconds = 0

        self.init_ui()
        self.load_config()

    def init_ui(self):
        self.setWindowTitle("Employee Tracker Pro")
        self.setFixedSize(340, 360)
        
        self.setStyleSheet("""
            QWidget { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Arial; }
            QLineEdit { background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 8px; color: #ffffff; }
            QPushButton { border-radius: 6px; padding: 10px; font-weight: bold; }
        """)

        layout = QVBoxLayout()

        self.label = QLabel("Employee Name:")
        self.label.setStyleSheet("color: #94a3b8; font-weight: 600;")
        layout.addWidget(self.label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter full name...")
        layout.addWidget(self.name_input)

        self.btn_toggle = QPushButton("Clock In")
        self.btn_toggle.setStyleSheet("background-color: #2563eb; color: white;")
        self.btn_toggle.clicked.connect(self.toggle_clock)
        layout.addWidget(self.btn_toggle)

        self.btn_break = QPushButton("Start Break")
        self.btn_break.setStyleSheet("background-color: #334155; color: #94a3b8;")
        self.btn_break.setEnabled(False)
        self.btn_break.clicked.connect(self.toggle_break)
        layout.addWidget(self.btn_break)

        self.status_frame = QFrame()
        self.status_frame.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 10px;")
        status_layout = QVBoxLayout(self.status_frame)

        self.status_label = QLabel("Status: Offline")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #64748b; font-weight: 600;")
        status_layout.addWidget(self.status_label)

        self.timer_label = QLabel("Work: 0h 0m | Break: 0h 0m")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("color: #38bdf8; font-size: 11px;")
        status_layout.addWidget(self.timer_label)

        layout.addWidget(self.status_frame)

        self.setLayout(layout)

        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.capture_and_sync)

        self.sec_timer = QTimer()
        self.sec_timer.timeout.connect(self.update_seconds)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show Window")
        show_action.triggered.connect(self.show)
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(QApplication.instance().quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                self.employee_name = data.get("employee_name", "")
                if self.employee_name:
                    self.name_input.setText(self.employee_name)
                    self.name_input.setDisabled(True)
            except Exception:
                pass

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"employee_name": self.employee_name}, f)

    def toggle_clock(self):
        if not self.is_tracking:
            name = self.name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Error", "Please enter Employee Name")
                return

            self.employee_name = name
            self.save_config()
            self.name_input.setDisabled(True)

            self.is_tracking = True
            self.btn_toggle.setText("Clock Out")
            self.btn_toggle.setStyleSheet("background-color: #dc2626; color: white;")
            
            self.btn_break.setEnabled(True)
            self.btn_break.setStyleSheet("background-color: #d97706; color: white;")
            
            self.status_label.setText("Status: Active Working")
            self.status_label.setStyleSheet("color: #22c55e; font-weight: 600;")
            
            self.sync_timer.start(SCREENSHOT_INTERVAL_MS)
            self.sec_timer.start(1000)
            self.capture_and_sync()
        else:
            self.is_tracking = False
            self.on_break = False
            
            self.sync_timer.stop()
            self.sec_timer.stop()

            self.btn_toggle.setText("Clock In")
            self.btn_toggle.setStyleSheet("background-color: #2563eb; color: white;")
            
            self.btn_break.setText("Start Break")
            self.btn_break.setEnabled(False)
            self.btn_break.setStyleSheet("background-color: #334155; color: #94a3b8;")

            self.status_label.setText("Status: Offline")
            self.status_label.setStyleSheet("color: #64748b; font-weight: 600;")

            # Final sync for totals on clock-out
            self.sync_data(active_window="Clocked Out")

            summary = SummaryDialog(self.work_seconds, self.break_seconds, self)
            summary.exec()

    def toggle_break(self):
        if not self.is_tracking:
            return

        if not self.on_break:
            self.on_break = True
            self.btn_break.setText("End Break")
            self.btn_break.setStyleSheet("background-color: #16a34a; color: white;")
            self.status_label.setText("Status: On Break ☕")
            self.status_label.setStyleSheet("color: #f59e0b; font-weight: 600;")
            self.sync_timer.stop()
            # Send Break Status to Server
            self.send_status_update(status="On Break")
        else:
            self.on_break = False
            self.btn_break.setText("Start Break")
            self.btn_break.setStyleSheet("background-color: #d97706; color: white;")
            self.status_label.setText("Status: Active Working")
            self.status_label.setStyleSheet("color: #22c55e; font-weight: 600;")
            self.sync_timer.start(SCREENSHOT_INTERVAL_MS)
            # Send Working Status to Server
            self.send_status_update(status="Active Working")

    def update_seconds(self):
        if self.is_tracking:
            if self.on_break:
                self.break_seconds += 1
            else:
                self.work_seconds += 1

            w_h = self.work_seconds // 3600
            w_m = (self.work_seconds % 3600) // 60
            b_h = self.break_seconds // 3600
            b_m = (self.break_seconds % 3600) // 60

            self.timer_label.setText(f"Work: {w_h}h {w_m}m | Break: {b_h}h {b_m}m")

    def send_status_update(self, status):
        """Sends immediate break status to server without waiting for screenshot."""
        try:
            data = {
                "employee_name": self.employee_name,
                "active_window": f"Status: {status}",
                "status": status,
                "work_seconds": self.work_seconds,
                "break_seconds": self.break_seconds
            }
            requests.post(SERVER_URL, data=data, timeout=3)
        except Exception:
            pass

    def capture_and_sync(self):
        if not self.is_tracking or self.on_break:
            return

        active_window = get_active_window_title()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shot_path = os.path.join(CACHE_DIR, f"{timestamp}.jpg")

        try:
            pyautogui.screenshot(shot_path)
            self.sync_data(active_window)
        except Exception:
            pass

    def sync_data(self, active_window):
        try:
            for cached_file in list(os.listdir(CACHE_DIR)):
                file_full_path = os.path.join(CACHE_DIR, cached_file)
                if not os.path.isfile(file_full_path):
                    continue

                with open(file_full_path, "rb") as f:
                    file_data = f.read()

                files = {"screenshot": (cached_file, file_data, "image/jpeg")}
                data = {
                    "employee_name": self.employee_name,
                    "active_window": active_window,
                    "status": "On Break" if self.on_break else "Active Working",
                    "work_seconds": self.work_seconds,
                    "break_seconds": self.break_seconds
                }
                res = requests.post(SERVER_URL, data=data, files=files, timeout=5)
                if res.status_code == 200:
                    os.remove(file_full_path)
        except Exception:
            pass


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = EmployeeApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()